import json
import argparse
from pathlib import Path


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="基于带注释的 DDL 和样本数据，生成表语义总结的 prompt")
    parser.add_argument("--input_file", type=str, default="../add_database_comments/output/final/annotated_ddl.jsonl",
                        help="最终 DDL 数据的输入文件路径")
    parser.add_argument("--template_file", type=str, default="prompts/sqlite_to_semantic_summary_prompt.txt",
                        help="prompt 模板文件路径（需包含 {sql_ddl} 和 {sample_data} 占位符）")
    parser.add_argument("--output_file", type=str, default="output/prompt/table_summary_prompts.jsonl",
                        help="生成的 prompt 输出文件路径")
    parser.add_argument("--ddl_field", type=str, default="annotated_ddl",
                        help="输入数据中带注释 DDL 的字段名")
    parser.add_argument("--sample_field", type=str, default="sample_data",
                        help="输入数据中样本数据的字段名")
    return parser.parse_args()


def main():
    args = parse_args()

    # 检查输入文件是否存在
    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    # 检查模板文件是否存在
    template_path = Path(args.template_file)
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_path}")

    # 确保输出目录存在
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 读取模板
    prompt_template = template_path.read_text(encoding="utf-8").strip()

    # 校验模板是否包含必要占位符（可选但推荐）
    required_placeholders = ["{sql_ddl}", "{sample_data}"]
    missing = [p for p in required_placeholders if p not in prompt_template]
    if missing:
        raise ValueError(f"模板中缺少必要占位符: {missing}")

    # 加载输入数据
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # 跳过损坏行

    print(f"共加载 {len(records)} 条 DDL 记录")

    # 生成 prompt 并保存
    processed_count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for data in records:
            # 检查必要字段是否存在
            if args.ddl_field not in data or args.sample_field not in data:
                continue

            ddl = data[args.ddl_field]
            sample = data[args.sample_field]

            # 填充模板
            filled_prompt = prompt_template.replace(
                "{sql_ddl}", ddl
            ).replace(
                "{sample_data}", json.dumps(sample, ensure_ascii=False, indent=2)
            )

            # 构建 prompt_context（与前序脚本结构一致）
            if "prompt_context" not in data:
                data["prompt_context"] = {}
            data["prompt_context"]["prompt_template"] = prompt_template
            data["prompt_context"]["filled"] = filled_prompt

            f.write(json.dumps(data, ensure_ascii=False) + "\n")
            processed_count += 1

    # 输出统计（保留中文提示）
    print(f"\n✅ 表语义总结 prompt 生成完成！")
    print(f"  成功处理: {processed_count} 条")
    print(f"  结果已保存至: {output_path}")


if __name__ == "__main__":
    main()