import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional
import sqlite3
import contextlib
import time


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="从后处理结果中提取最终所需的结构化 DDL 数据")
    parser.add_argument(
        "--input_file",
        type=str,
        default="output/postprocessed/static_requirement_matching/sql_responses.jsonl",
        help="后处理结果的输入文件路径"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="output/final/static_requirement_matching/annotated_ddl.jsonl",
        help="最终输出文件路径"
    )
    return parser.parse_args()


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """从 JSONL 文件加载记录，跳过无效行"""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def main():
    args = parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 加载原始记录
    records = load_jsonl(input_path)
    print(f"共加载 {len(records)} 条后处理记录")

    final_records = []

    for record in records:
        structured_response = record['structured_response']

        is_requirement_matched = structured_response['is_requirement_matched']
        mismatch_details = structured_response['mismatch_details']

        if len(mismatch_details)>0:
            continue
        if is_requirement_matched is False:
            continue

        del record['structured_response']
        del record['generated_content']
        del record['model_name']

        final_records.append(record)

    # 保存结果
    with open(output_path, "w", encoding="utf-8") as f:
        for record in final_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 输出统计信息
    print(f"\n✅ 最终数据生成完成！")
    print(f"  输入记录数: {len(records)}")
    print(f"  验证成功: {len(final_records)}")
    print(f"  验证失败: {len(records) - len(final_records)}")
    print(f"  最终输出记录数: {len(final_records)}")
    print(f"  结果已保存至: {output_path}")


if __name__ == "__main__":
    main()