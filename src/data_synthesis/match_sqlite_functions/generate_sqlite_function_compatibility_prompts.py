
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm


def parse_args():
    parser = argparse.ArgumentParser(
        description="基于表及其相似表的结构，为每个 SQLite 函数分组生成兼容性判断 Prompt"
    )
    parser.add_argument(
        "--input_file",
        type=str,
        default="../vector_table_similarity/output/final/similarity_enhanced_tables.jsonl",
        help="包含表及其相似表信息的输入文件（JSONL）"
    )
    parser.add_argument(
        "--sqlite_functions_file",
        type=str,
        default="sqlite_functions_groups.json",
        help="SQLite 函数分组定义文件（JSON）"
    )
    parser.add_argument(
        "--prompt_template_file",
        type=str,
        default="prompts/sqlite_schema_function_compatibility_prompt.txt",
        help="Prompt 模板文件路径"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="output/prompts/function_compatibility_prompts.jsonl",
        help="生成的 Prompt 输出文件（JSONL）"
    )
    return parser.parse_args()


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
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


def load_json(file_path: str) -> Any:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prompt_template(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_multi_table_context(main_table: Dict[str, Any], similar_tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """构建包含主表和相似表的上下文结构（仅保留必要字段）"""
    context = [{
        "table_name": main_table["table_name"],
        "create_sql": main_table.get("annotated_ddl", main_table.get("create_sql", "")),
        "sample_data": main_table.get("sample_data", "")
    }]

    for sim in similar_tables:
        context.append({
            "table_name": sim.get("table_name", ""),
            "create_sql": sim.get("annotated_ddl", sim.get("create_sql", "")),
            "sample_data": sim.get("sample_data", "")
        })
    return context


def main():
    args = parse_args()

    # 确保输出目录存在
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 加载数据
    print(f"加载表数据: {args.input_file}")
    table_records = load_jsonl(args.input_file)
    print(f"加载 {len(table_records)} 张表")

    print(f"加载 SQLite 函数分组: {args.sqlite_functions_file}")
    function_groups = load_json(args.sqlite_functions_file)
    print(f"加载 {len(function_groups)} 个函数分组")

    print(f"加载 Prompt 模板: {args.prompt_template_file}")
    prompt_template = load_prompt_template(args.prompt_template_file)

    generated_prompts = []
    prompt_idx = 0

    for table_data in tqdm(table_records):
        # 构建多表上下文（主表 + 相似表）
        multi_table_context = build_multi_table_context(
            main_table=table_data,
            similar_tables=table_data.get("similar_tables", [])
        )

        # 为每个函数分组生成一个 Prompt
        for func_group in function_groups:
            try:
                name = func_group["name"]
                description = func_group["description"]
                suitable = func_group.get("suitable_schemas", "")
                unsuitable = func_group.get("unsuitable_schemas", "")
                key_funcs = func_group.get("key_functions", [])
            except KeyError as e:
                print(f"⚠️ 函数分组缺少必要字段 {e}，跳过: {func_group.get('name', 'unknown')}")
                continue

            # 渲染 Prompt
            filled_prompt = (
                prompt_template
                .replace("{FUNCTION_GROUP_NAME}", name)
                .replace("{FUNCTION_GROUP_DESCRIPTION}", description)
                .replace("{SUITABLE_SCHEMA_CHARACTERISTICS}", suitable)
                .replace("{UNSUITABLE_SCHEMA_CHARACTERISTICS}", unsuitable)
                .replace("{KEY_FUNCTIONS}", json.dumps(key_funcs, ensure_ascii=False, indent=2))
                .replace("{MULTI_TABLE_SCHEMA_WITH_SAMPLES}", json.dumps(multi_table_context, ensure_ascii=False, indent=2))
            )

            # 构建输出记录：一张表 + 一个函数组 = 一条记录
            output_record = {
                "prompt_id": prompt_idx,
            }

            output_record.update(table_data)

            output_record['prompt_context'] = {}
            output_record['prompt_context']['template'] = prompt_template
            output_record['prompt_context']['filled'] = filled_prompt

            generated_prompts.append(output_record)
            prompt_idx += 1

    # 保存结果
    with open(output_path, "w", encoding="utf-8") as f:
        for record in generated_prompts:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n✅ Prompt 生成完成！")
    print(f"  总 Prompt 数量: {len(generated_prompts)}")
    print(f"  输出文件: {output_path}")


if __name__ == "__main__":
    main()