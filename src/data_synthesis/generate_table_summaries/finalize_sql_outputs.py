import json
import argparse
from pathlib import Path


def get_nested_value(obj, key_path, default=None):
    """
    从嵌套字典中按点号路径（如 'a.b.c'）安全获取值。
    若路径不存在，返回 default。
    """
    keys = key_path.split(".")
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="从后处理结果中提取最终所需的结构化 DDL 数据")
    parser.add_argument("--input_file", type=str, default="output/postprocessed/sql_responses.jsonl",
                        help="后处理结果的输入文件路径")
    parser.add_argument("--output_file", type=str, default="output/final/annotated_ddl.jsonl",
                        help="最终输出文件路径")
    parser.add_argument(
        "--fields",
        nargs="+",
        default=["table_name", "create_sql", "sample_data", "annotated_ddl", "structured_response.summary"],
        help="需要保留的字段列表（支持嵌套字段路径，如 'structured_response.summary'）"
    )
    parser.add_argument(
        "--rename_from",
        type=str,
        default="structured_response.summary",
        help="要重命名的源字段路径（必须在 --fields 中）"
    )
    parser.add_argument(
        "--rename_to",
        type=str,
        default="table_summary",  # ← 语义化命名：表的总结
        help="重命名后的目标字段名（设为空字符串 '' 可禁用重命名）"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

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
                    continue

    print(f"共加载 {len(records)} 条后处理记录")

    final_records = []
    skipped_count = 0

    for item in records:
        # 提取所有指定字段（支持嵌套）
        extracted = {}
        missing = False
        for field in args.fields:
            value = get_nested_value(item, field)
            if value is None:  # 注意：如果原值就是 None，也会被跳过
                missing = True
                break
            # 使用字段的最后一段作为键（如 'structured_response.summary' → 'summary'）
            # 但为了支持 rename，我们先保留原 field 名作为临时键
            extracted[field] = value

        if missing:
            skipped_count += 1
            continue

        # 构建最终记录：先用字段原名（或简化名），再处理 rename
        final_item = {}
        for field in args.fields:
            # 决定输出时的字段名：默认用字段路径的最后一段
            output_key = field.split(".")[-1] if "." in field else field
            final_item[output_key] = extracted[field]

        # 执行重命名：如果 rename_to 非空 且 rename_from 在 fields 中
        if args.rename_to and args.rename_from in args.fields:
            # rename_from 对应的输出键（通常是 'summary'）
            temp_key = args.rename_from.split(".")[-1]
            if temp_key in final_item:
                final_item[args.rename_to] = final_item.pop(temp_key)

        final_records.append(final_item)

    # 保存结果
    with open(output_path, "w", encoding="utf-8") as f:
        for record in final_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 输出统计信息
    print(f"\n✅ 最终数据生成完成！")
    print(f"  输入记录数: {len(records)}")
    print(f"  成功生成: {len(final_records)} 条")
    if skipped_count > 0:
        print(f"  跳过缺失字段的记录: {skipped_count} 条")
    print(f"  结果已保存至: {output_path}")


if __name__ == "__main__":
    main()