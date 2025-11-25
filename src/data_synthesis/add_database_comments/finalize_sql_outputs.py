import json
import argparse
from pathlib import Path


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="从后处理结果中提取最终所需的结构化 DDL 数据")
    parser.add_argument("--input_file", type=str, default="output/postprocessed/sql_responses.jsonl",
                        help="后处理结果的输入文件路径")
    parser.add_argument("--output_file", type=str, default="output/final/annotated_ddl.jsonl",
                        help="最终输出文件路径")
    parser.add_argument("--fields", nargs="+", default=["table_name", "create_sql", "sample_data", "extracted_sql"],
                        help="需要保留的字段列表（从输入记录中提取）")
    parser.add_argument("--rename_from", type=str, default="extracted_sql",
                        help="要重命名的源字段名（若该字段在 --fields 中且存在，则会被重命名）")
    parser.add_argument("--rename_to", type=str, default="annotated_ddl",
                        help="重命名后的目标字段名（设为空字符串 '' 可禁用重命名）")
    return parser.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    # 确保输出目录存在
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 加载数据
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # 跳过损坏行

    print(f"共加载 {len(records)} 条后处理记录")

    # 构建最终输出
    final_records = []
    missing_field_count = 0

    for item in records:
        # 检查是否包含所有指定字段
        if not all(field in item for field in args.fields):
            missing_field_count += 1
            continue

        # 提取指定字段
        final_item = {field: item[field] for field in args.fields}

        # 执行重命名（如果启用）
        if args.rename_to and args.rename_from in final_item:
            final_item[args.rename_to] = final_item.pop(args.rename_from)

        final_records.append(final_item)

    # 保存结果
    with open(output_path, "w", encoding="utf-8") as f:
        for record in final_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 输出统计信息（保留中文提示）
    print(f"\n✅ 最终数据生成完成！")
    print(f"  输入记录数: {len(records)}")
    print(f"  成功生成: {len(final_records)} 条")
    if missing_field_count > 0:
        print(f"  跳过缺失字段的记录: {missing_field_count} 条")
    print(f"  结果已保存至: {output_path}")


if __name__ == "__main__":
    main()