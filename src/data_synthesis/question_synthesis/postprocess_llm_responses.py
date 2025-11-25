import json
import os
import re
import argparse
from pathlib import Path
from tqdm import tqdm
import json_repair


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="从 LLM 原始响应中提取并清洗 SQL 语句")
    parser.add_argument("--input_dir", type=str, default="output/llm_raw",
                        help="LLM 原始响应的输入目录（会递归读取所有 .jsonl 文件）")
    parser.add_argument("--output_file", type=str, default="output/postprocessed/sql_responses.jsonl",
                        help="清洗后结果的输出文件路径")
    return parser.parse_args()


def parse_structured_response_from_content(content: str) -> dict | None:
    """
    从 LLM 响应文本中解析出结构化的 JSON 对象。
    支持跳过 <think>...</think> 等思考标记，尝试修复并加载 JSON 内容。
    """
    # 移除思考部分（兼容不同格式）
    if "</think>" in content:
        match = re.search(r"</think>(.*?)$", content, re.DOTALL)
        if match:
            content = match.group(1).strip()
        else:
            content = ""  # 无法提取有效内容

    if not content:
        return None

    try:
        return re.search("\[QUESTION-START\](.*?)\[QUESTION-END\]", content, re.DOTALL).group(1).strip()
    except Exception:
        pass  # 忽略解析失败

    return None


def load_all_responses(input_dir: str) -> list:
    """递归加载 input_dir 下所有 .jsonl 文件中的响应记录"""
    responses = []
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    for file_path in input_path.rglob("*.jsonl"):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    responses.append(data)
                except json.JSONDecodeError:
                    continue  # 跳过损坏行
    return responses


def main():
    args = parse_args()

    # 确保输出目录存在
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 加载所有原始响应
    print(f"正在从 '{args.input_dir}' 加载 LLM 响应...")
    raw_responses = load_all_responses(args.input_dir)
    print(f"共加载 {len(raw_responses)} 条原始响应")

    # 2. 提取并过滤结构化响应
    processed_responses = []
    failed_count = 0

    for record in tqdm(raw_responses, desc="解析结构化响应"):
        content = record.get("generated_content", "")
        if not content:
            failed_count += 1
            continue

        structured_response = parse_structured_response_from_content(content)

        if structured_response is None:
            failed_count += 1
            continue

        # 将解析出的结构化内容存入新字段
        record["structured_response"] = structured_response
        processed_responses.append(record)

    # 3. 保存结果
    with open(output_path, "w", encoding="utf-8") as f:
        for data in processed_responses:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    # 4. 输出统计信息
    success_count = len(processed_responses)
    total = len(raw_responses)
    print(f"\n✅ 处理完成！")
    print(f"  总响应数: {total}")
    print(f"  成功提取结构化响应: {success_count}")
    print(f"  无法解析的数量: {failed_count}")
    print(f"  结果已保存至: {output_path}")


if __name__ == "__main__":
    main()