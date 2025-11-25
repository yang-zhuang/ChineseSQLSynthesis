import json
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI, APIError
from tqdm import tqdm
from pathlib import Path  # 需要导入pathlib
import random

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key=""
)

base_url = "http://192.168.2.3:42434/v1"
# model_name = 'Qwen3-4B-Instruct-2507-FP8'
# model_name = "Qwen3-32B"
model_name = "Qwen3-30B-A3B"

client = OpenAI(
    base_url=base_url,
    api_key=""
)

enable_thinking = False


def process_single_prompt(prompt: str, index: int, timeout:int=30, enable_thinking=False) -> tuple:
    """处理单个prompt，返回原始索引+生成结果"""
    if "think" not in model_name.lower():
        if enable_thinking:
            pass
        else:
            prompt += "\n/no_think"

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                # {'role': 'system', 'content': 'You are a helpful assistant specializing in database DDL comments.'},
                {'role': 'user', 'content': prompt}
            ],
            stream=False,
            timeout=timeout
        )
        return (index, response.choices[0].message.content)
    except Exception as e:
        print(f"索引{index}未知错误: {str(e)}")
        return (index, f"ERROR: {str(e)}")


def load_processed_indices(output_file: str) -> set:
    """加载已处理的索引"""
    processed_indices = set()

    output_path = Path(output_file)  # 转换为Path对象
    for root, dirs, files in os.walk(output_path.parent):  # 使用Path对象的parent
        for file in files:
            if 'jsonl' not in file:
                continue

            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    processed_indices.add(data['index'])
    return processed_indices


def save_single_result(output_file: str, index: int, original_data: dict, generated_content: str):
    """保存单条结果到JSONL文件"""
    result_item = {
        "index": index,
        "original_data": original_data,
        "model_name": model_name,
        "generated_content": generated_content,
        "process_time": datetime.now().isoformat()
    }

    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result_item, ensure_ascii=False) + "\n")


def llm_batch_inference(prompts: list, original_data: list, output_file: str, max_workers: int = 5, enable_thinking=False) -> list:
    """批量处理prompt，支持断点续处理"""
    # 加载已处理的索引
    processed_indices = load_processed_indices(output_file)

    # 构建待处理的任务列表（索引，prompt，原始数据）
    tasks = []
    for idx, (prompt, data) in enumerate(zip(prompts, original_data)):
        if idx not in processed_indices:
            tasks.append((idx, prompt, data))

    print(f"总数据量: {len(prompts)}，已处理: {len(processed_indices)}，待处理: {len(tasks)}")

    if not tasks:
        print("所有数据已处理完成！")
        return []

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交任务
        future_to_index = {
            executor.submit(process_single_prompt, prompt, idx, 120, enable_thinking): (idx, data)
            for idx, prompt, data in tasks
        }

        # 处理完成的任务
        for future in tqdm(as_completed(future_to_index), total=len(tasks), desc="LLM生成中"):
            idx, original_data_item = future_to_index[future]
            try:
                result_idx, generated_content = future.result()

                if "error" in generated_content.lower():
                    continue

                # 立即保存单条结果
                save_single_result(output_file, result_idx, original_data_item, generated_content)
                results.append({
                    "index": result_idx,
                    "model_name": model_name,
                    "generated_content": generated_content
                })
            except Exception as e:
                print(f"索引{idx}任务执行异常: {str(e)}")
                continue
                # 即使出错也保存错误信息，避免重复处理
                save_single_result(output_file, idx, original_data_item, f"ERROR: 任务执行异常 - {str(e)}")
                results.append({
                    "index": idx,
                    "generated_content": f"ERROR: 任务执行异常 - {str(e)}"
                })

    return results


def get_output_filename(save_dir='result') -> str:
    """生成带时间戳的输出文件名"""
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    return f"{save_dir}/{timestamp}.jsonl"


if __name__ == '__main__':
    # 1. 加载原始prompt数据
    prompt_input_path = "prompts/question_synthesis_prompts_zh_doris.json"
    doris_prompt_data = []

    if prompt_input_path.endswith(".jsonl"):
        with open(prompt_input_path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)

                doris_prompt_data.append(data)

    elif prompt_input_path.endswith(".json"):
        with open(prompt_input_path, "r", encoding="utf-8") as f:
            doris_prompt_data = json.load(f)

    print(f"成功加载{len(doris_prompt_data)}条prompt数据")

    random.shuffle(doris_prompt_data)

    # 2. 设置输出文件
    output_file = get_output_filename(save_dir='doris_question_synthesis_result')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    print(f"输出文件: {output_file}")

    # 3. 提取原始prompt列表
    prompts = [item['doris_question_synthesis']["prompt"] for item in doris_prompt_data]

    # 4. 批量调用LLM（支持断点续处理）
    generated_contents = llm_batch_inference(
        prompts=prompts,
        original_data=doris_prompt_data,
        output_file=output_file,
        max_workers=10,  # 可根据需要调整并发数
        enable_thinking=enable_thinking
    )

    print(f"处理完成！结果已保存至: {output_file}")

    # 5. 可选：生成完整的合并文件（用于后续处理）
    if generated_contents:
        complete_output_file = output_file.replace(".jsonl", "_complete.json")
        complete_data = []
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    complete_data.append(item)

        # 按索引排序
        complete_data.sort(key=lambda x: x["index"])

        with open(complete_output_file, "w", encoding="utf-8") as f:
            json.dump(complete_data, f, ensure_ascii=False, indent=2)
        print(f"完整合并文件已保存至: {complete_output_file}")