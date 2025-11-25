import json
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from tqdm import tqdm
from pathlib import Path


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="批量调用 LLM 进行推理并支持断点续跑")
    parser.add_argument("--prompt_file", type=str, default='output/prompt/generated_prompts.jsonl',
                        help="输入的 prompt 文件路径（支持 .json 或 .jsonl）")
    parser.add_argument("--output_dir", type=str, default="output/llm_raw",
                        help="大模型原始响应的输出目录（建议与其他处理阶段目录区分）")
    parser.add_argument("--model_name", type=str, default="Qwen3-30B-A3B",
                        help="要调用的模型名称")
    parser.add_argument("--base_url", type=str, default="http://localhost:8000/v1",
                        help="OpenAI 兼容 API 的 base URL")
    parser.add_argument("--api_key", type=str, default="dummy-key",
                        help="API 密钥（本地部署通常为空）")
    parser.add_argument("--max_workers", type=int, default=10,
                        help="并发线程数")
    parser.add_argument("--timeout", type=int, default=120,
                        help="单个请求的超时时间（秒）")
    parser.add_argument("--enable_thinking", action="store_true",
                        help="启用思考模式（仅对支持 think 的模型有效）")
    parser.add_argument("--id_fields", nargs="*", default=['prompt_id'],
                        help="用于判断是否已处理的唯一标识字段（多个字段组合）")
    parser.add_argument("--prompt_field", type=str, default='question_synthesis_metadata.prompt',
                        help="JSON 数据中 prompt 内容的字段路径，使用点号分隔，如 'text' 或 'messages.0.content'")
    return parser.parse_args()


def get_output_filename(save_dir: str) -> str:
    """生成带时间戳的输出文件路径"""
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    return str(save_path / f"{timestamp}.jsonl")


def get_nested_value(data: dict, field_path: str):
    """
    根据点号分隔的字段路径（如 'prompt_context.filled'）从嵌套字典中安全获取值。
    若路径不存在，抛出 KeyError 并提示字段缺失。
    """
    keys = field_path.split('.')
    current = data
    try:
        for key in keys:
            if key.isdigit():  # 支持数组索引，如 messages.0.content
                key = int(key)
            current = current[key]
        return current
    except (KeyError, IndexError, TypeError) as e:
        raise KeyError(f"数据中缺少字段路径 '{field_path}'（错误: {e}）")


def load_processed_records(output_dir: str, id_fields: list) -> set:
    """加载已处理记录的唯一标识元组集合，用于快速去重"""
    processed = set()
    output_path = Path(output_dir)

    if not output_path.exists():
        return processed

    for file_path in output_path.rglob("*.jsonl"):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    key = tuple(data.get(field) for field in id_fields)
                    if all(k is not None for k in key):
                        processed.add(key)
                except (json.JSONDecodeError, KeyError):
                    continue  # 跳过格式错误或缺失字段的行
    return processed


def save_single_result(output_file: str, original_data:dict, generated_content: str, model_name: str):
    """保存单条结果到输出文件"""
    record = original_data.copy()
    record["model_name"] = model_name
    record["generated_content"] = generated_content
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_single_prompt(client, model_name: str, prompt: str, index: int, timeout: int,
                          enable_thinking: bool) -> tuple:
    """处理单个 prompt 请求"""
    # 自动附加 /no_think（若模型不支持思考）
    if "think" not in model_name.lower() and not enable_thinking:
        prompt += "\n/no_think"

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            timeout=timeout
        )
        content = response.choices[0].message.content
        return index, content
    except Exception as e:
        return index, f"ERROR: {str(e)}"


def load_input_data(prompt_file: str) -> list:
    """加载原始 prompt 数据（支持 .json 或 .jsonl）"""
    input_path = Path(prompt_file)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    original_data = []
    if input_path.suffix == ".jsonl":
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                original_data.append(json.loads(line.strip()))
    elif input_path.suffix == ".json":
        with open(input_path, "r", encoding="utf-8") as f:
            original_data = json.load(f)
    else:
        raise ValueError("仅支持 .json 或 .jsonl 格式的输入文件")

    print(f"原始数据共 {len(original_data)} 条")
    return original_data


def filter_unprocessed_items(original_data: list, output_dir: str, id_fields: list) -> list:
    """根据输出目录中已存在的记录，筛选出尚未处理的数据项"""
    processed_keys = load_processed_records(output_dir, id_fields)
    print(f"已处理记录数（按唯一键去重）: {len(processed_keys)}")

    unprocessed_data = []
    for item in original_data:
        key = tuple(item.get(field) for field in id_fields)
        if not all(k is not None for k in key):
            print(f"警告：跳过缺失唯一标识字段的数据项: {item}")
            continue
        if key not in processed_keys:
            unprocessed_data.append(item)

    print(f"待处理数据: {len(unprocessed_data)} 条")
    return unprocessed_data


def extract_prompts(data_list: list, prompt_field: str) -> list:
    """根据指定字段路径从数据列表中提取 prompt 文本"""
    prompts = []
    for item in data_list:
        try:
            prompt_text = get_nested_value(item, prompt_field)
            prompts.append(prompt_text)
        except KeyError as e:
            raise KeyError(f"无法提取 prompt：{e}")
    return prompts


def run_batch_inference(client, model_name: str, prompts: list, unprocessed_data: list, output_file: str, max_workers: int, timeout: int, enable_thinking: bool) -> int:
    """执行批量 LLM 推理并实时保存结果"""
    results_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {
            executor.submit(
                process_single_prompt,
                client, model_name, prompt, idx, timeout, enable_thinking
            ): (idx, item)
            for idx, (prompt, item) in enumerate(zip(prompts, unprocessed_data))
        }

        for future in tqdm(as_completed(future_to_item), total=len(unprocessed_data), desc="LLM 生成中"):
            idx, item = future_to_item[future]
            try:
                result_idx, generated_content = future.result()

                # 跳过明显错误的结果
                if isinstance(generated_content, str) and "error" in generated_content.lower():
                    print(f"跳过错误结果（索引 {result_idx}）: {generated_content[:100]}...")
                    continue

                save_single_result(output_file, item, generated_content, model_name)
                results_count += 1
            except Exception as e:
                print(f"处理索引 {idx} 时发生异常: {e}")
                continue

    return results_count


def main():
    args = parse_args()

    # 初始化 OpenAI 兼容客户端
    client = OpenAI(base_url=args.base_url, api_key=args.api_key)

    # 生成带时间戳的输出文件
    output_file = get_output_filename(args.output_dir)
    print(f"输出文件: {output_file}")

    # 1. 加载原始 prompt 数据
    original_data = load_input_data(args.prompt_file)

    # 2. 筛选尚未处理的数据项
    unprocessed_data = filter_unprocessed_items(original_data, args.output_dir, args.id_fields)

    if not unprocessed_data:
        print("✅ 所有数据均已处理完毕，无需继续。")
        return

    # 3. 根据命令行指定的字段路径提取 prompt
    prompts = extract_prompts(unprocessed_data, args.prompt_field)

    # 4. 批量调用 LLM（支持断点续处理）
    generated_count = run_batch_inference(
        client=client,
        model_name=args.model_name,
        prompts=prompts,
        unprocessed_data=unprocessed_data,
        output_file=output_file,
        max_workers=args.max_workers,
        timeout=args.timeout,
        enable_thinking=args.enable_thinking
    )

    print(f"✅ 处理完成！结果已保存至: {output_file}")
    print(f"本次成功生成: {generated_count} 条")


if __name__ == "__main__":
    main()