import json
import os
import argparse
from typing import List, Dict, Any


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """从 JSONL 文件加载数据"""
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def load_prompt_template(template_path: str) -> str:
    """加载 prompt 模板文件"""
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def ensure_string_schema(schema) -> str:
    """确保 schema 为字符串格式，若为列表则用空行连接"""
    if isinstance(schema, list):
        return "\n\n".join(schema)
    return str(schema)


def generate_correction_prompt(
    template: str,
    sql: str,
    error_message: str,
    schema: str
) -> str:
    """根据模板生成 SQL 修正 prompt"""
    return (
        template
        .replace("[SQL语句内容]", sql)
        .replace("[错误信息内容]", error_message)
        .replace("{schema}", schema)
    )


def save_jsonl(data: List[Dict], output_path: str) -> None:
    """将数据保存为 JSONL 格式"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush()


def main():
    parser = argparse.ArgumentParser(description="为 SQL 验证失败的案例生成修正 prompt")
    parser.add_argument(
        "--input_file",
        type=str,
        default="../sql_synthesis/output/failed/failed_ddl.jsonl",
        help="输入的失败案例 JSONL 文件路径"
    )
    parser.add_argument(
        "--prompt_template",
        type=str,
        default="prompts/sql_correction_prompt.txt",
        help="SQL 修正 prompt 模板文件路径"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="./output/prompt/generated_prompts.jsonl",
        help="输出的 JSONL 文件路径"
    )

    args = parser.parse_args()

    # 1. 加载失败案例
    print("正在加载失败的 SQL 案例...")
    failed_cases = load_jsonl(args.input_file)
    print(f"共加载 {len(failed_cases)} 条失败记录")

    # 2. 加载 prompt 模板
    prompt_template = load_prompt_template(args.prompt_template)

    # 3. 为每条记录生成修正 prompt
    print("正在生成修正 prompt...")
    for case in failed_cases:
        validation_error = case['validation_error']
        sql = validation_error['sql']
        error_message = validation_error['error_message']
        schema = case['prompt_context']['metadata']['schema_str']

        schema_str = ensure_string_schema(schema)
        correction_prompt = generate_correction_prompt(
            template=prompt_template,
            sql=sql,
            error_message=error_message,
            schema=schema_str
        )

        # 将生成的 prompt 存入结构（使用清晰字段名）
        validation_error['correction_prompt'] = correction_prompt

    # 4. 保存结果
    save_jsonl(failed_cases, args.output_file)
    print(f"结果已保存至: {args.output_file}")


if __name__ == "__main__":
    main()