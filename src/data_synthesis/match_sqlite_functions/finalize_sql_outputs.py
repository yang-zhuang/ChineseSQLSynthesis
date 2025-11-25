import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

# 常量定义（避免硬编码）
FUNCTION_DESCRIPTION_FILE = "sqlite_functions_zh_description.jsonl"


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="从后处理结果中提取最终所需的结构化 DDL 数据")
    parser.add_argument(
        "--input_file",
        type=str,
        default="output/postprocessed/sql_responses.jsonl",
        help="后处理结果的输入文件路径"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="output/final/annotated_ddl.jsonl",
        help="最终输出文件路径"
    )
    parser.add_argument(
        "--function_desc_file",
        type=str,
        default=FUNCTION_DESCRIPTION_FILE,
        help="SQLite 函数中文描述文件路径"
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


def group_records_by_table_ddl(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按 table_name 和 create_sql 对记录进行分组，合并 structured_response"""
    grouped = []
    for record in records:
        # 查找是否存在相同表名和 DDL 的分组
        match_idx = None
        for idx, group in enumerate(grouped):
            if (group["table_name"] == record["table_name"] and
                group["create_sql"] == record["create_sql"]):
                match_idx = idx
                break

        if match_idx is not None:
            # 合并 structured_response
            grouped[match_idx]["structured_response_list"].append(record["structured_response"])
        else:
            # 新建分组
            new_group = {
                "table_name": record["table_name"],
                "create_sql": record["create_sql"],
                "sample_data": record["sample_data"],
                "annotated_ddl": record["annotated_ddl"],
                "table_summary": record["table_summary"],
                "similar_tables": record["similar_tables"],
                "structured_response_list": [record["structured_response"]]
            }
            grouped.append(new_group)
    return grouped


def extract_applicable_functions(
    grouped_records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """从分组记录中提取有效的 key_functions，并过滤无函数的分组"""
    valid_records = []
    no_function_count = 0

    for group in grouped_records:
        all_functions = []
        for response in group["structured_response_list"]:
            if not response.get("suitable", False):
                continue
            key_funcs = response.get("key_functions", [])
            if key_funcs:
                all_functions.extend(key_funcs)

        if not all_functions:
            no_function_count += 1
            continue

        # 去重（可选，若顺序不重要可转为 set）
        unique_functions = list(dict.fromkeys(all_functions))  # 保持顺序去重

        # 移除中间字段，添加函数列表
        new_record = {k: v for k, v in group.items() if k != "structured_response_list"}
        new_record["applicable_functions"] = unique_functions
        valid_records.append(new_record)

    print(f"分组后记录数: {len(grouped_records)}，其中无适用函数的记录数: {no_function_count}")
    return valid_records


def load_function_descriptions(file_path: Path) -> Dict[str, str]:
    """加载 SQLite 函数的中文描述映射"""
    descriptions = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                descriptions.update(data)
    return descriptions


def attach_function_descriptions(
    records: List[Dict[str, Any]],
    func_desc_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    """为每条记录附加函数描述，仅保留有描述的函数"""
    final_records = []
    for record in records:
        func_desc_pairs = {
            func: func_desc_map[func]
            for func in record["applicable_functions"]
            if func in func_desc_map
        }

        if not func_desc_pairs:
            continue  # 跳过无描述的函数记录

        # 移除中间字段，替换为带描述的字段
        new_record = {k: v for k, v in record.items() if k != "applicable_functions"}
        new_record["function_descriptions"] = func_desc_pairs
        final_records.append(new_record)

    return final_records


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

    # 2. 按表名 + DDL 分组
    grouped_records = group_records_by_table_ddl(records)

    # 3. 提取有效的适用函数
    records_with_functions = extract_applicable_functions(grouped_records)

    # 4. 加载函数描述
    func_desc_file = Path(args.function_desc_file)
    if not func_desc_file.exists():
        raise FileNotFoundError(f"函数描述文件不存在: {func_desc_file}")
    function_descriptions = load_function_descriptions(func_desc_file)
    print(f"成功加载 {len(function_descriptions)} 个函数的中文描述")

    # 5. 附加函数描述，过滤无描述项
    final_records = attach_function_descriptions(records_with_functions, function_descriptions)

    # 6. 保存结果
    with open(output_path, "w", encoding="utf-8") as f:
        for record in final_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 7. 输出统计信息
    print(f"\n✅ 最终数据生成完成！")
    print(f"  输入记录数: {len(records)}")
    print(f"  最终输出记录数: {len(final_records)}")
    print(f"  结果已保存至: {output_path}")


if __name__ == "__main__":
    main()