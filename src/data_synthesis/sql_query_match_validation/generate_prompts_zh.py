import json
import os
import argparse
from tqdm import tqdm
from typing import List, Dict, Optional
import copy


def load_jsonl_data(file_path: str) -> List[Dict]:
    """从 JSONL 文件中加载数据"""
    data_list = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data_list.append(json.loads(line))
    return data_list


def load_prompt_template(template_path: str) -> str:
    """加载 prompt 模板文件"""
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"模板文件未找到: {template_path}")
    except Exception as e:
        raise RuntimeError(f"加载模板失败 ({template_path}): {e}")


def generate_static_matching_item(item: Dict, template: str) -> Dict:
    """为单个条目生成静态需求匹配数据"""
    synthesis_question = item['synthesis_question']
    synthesis_sql = item['synthesis_sql']
    schema = item['question_synthesis_metadata']['schema']
    engine = item['question_synthesis_metadata']['engine']

    filled_prompt = (
        template
        .replace("{db_type}", engine)
        .replace("{database_schema}", schema)
        .replace("{user_query}", synthesis_question)
        .replace("{generated_sql}", synthesis_sql)
    )

    static_matching = {
        "prompt": filled_prompt,
        "sql": synthesis_sql,
        "query": synthesis_question,
        "schema": schema
    }

    result_item = copy.deepcopy(item)
    result_item["static_requirement_matching"] = static_matching
    return result_item


def generate_dynamic_matching_item(item: Dict, template: str) -> Optional[Dict]:
    """为单个条目生成动态需求匹配数据（若样本数据存在）"""
    synthesis_question = item['synthesis_question']
    synthesis_sql = item['synthesis_sql']
    schema = item['question_synthesis_metadata']['schema']
    engine = item['question_synthesis_metadata']['engine']

    try:
        sample_data = item['prompt_context']['metadata']['db_value_prompt']
    except KeyError:
        return None  # 缺少样本数据，跳过

    filled_prompt = (
        template
        .replace("{db_type}", engine)
        .replace("{table_schemas}", schema)
        .replace("{column_values}", json.dumps(sample_data, ensure_ascii=False, indent=2))
        .replace("{user_query}", synthesis_question)
        .replace("{generated_sql}", synthesis_sql)
    )

    dynamic_matching = {
        "prompt": filled_prompt,
        "sql": synthesis_sql,
        "query": synthesis_question,
        "schema": schema,
        "sample_data": sample_data
    }

    result_item = copy.deepcopy(item)
    result_item["dynamic_requirement_matching"] = dynamic_matching
    return result_item


def save_as_jsonl(data: List[Dict], output_path: str) -> None:
    """将数据保存为 JSONL 格式（每行一个 JSON 对象）"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"数据已保存至: {output_path}（共 {len(data)} 条）")
    except Exception as e:
        print(f"保存文件失败 ({output_path}): {e}")


def main():
    parser = argparse.ArgumentParser(description="生成静态和/或动态需求匹配的 prompt 数据（支持 JSONL 输出）")
    parser.add_argument(
        "--input_file",
        type=str,
        default="../question_synthesis/output/final/annotated_ddl.jsonl",
        help="输入的 JSONL 文件路径（默认: ../question_synthesis/output/final/annotated_ddl.jsonl）"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./output/prompt",
        help="输出目录路径（默认: ./output/prompt）"
    )
    parser.add_argument(
        "--static_template",
        type=str,
        default="prompts/static_requirement_matching_prompt.txt",
        help="静态 prompt 模板文件路径（默认: prompts/static_requirement_matching_prompt.txt）"
    )
    parser.add_argument(
        "--dynamic_template",
        type=str,
        default="prompts/dynamic_requirement_matching_prompt.txt",
        help="动态 prompt 模板文件路径（默认: prompts/dynamic_requirement_matching_prompt.txt）"
    )

    args = parser.parse_args()

    # 兼容“仅使用一种模板”的需求：允许用户通过传入空字符串或 'none' 禁用某一项
    # 例如: --static_template "" 或 --static_template none
    def is_disabled(val):
        return val in ("", "none", "None", None)

    use_static = not is_disabled(args.static_template)
    use_dynamic = not is_disabled(args.dynamic_template)

    if not use_static and not use_dynamic:
        raise ValueError("错误：至少需要启用 --static_template 或 --dynamic_template（可传入空值或 'none' 禁用某一项）")

    # 构建输出路径（仅启用的才定义）
    static_output_path = os.path.join(args.output_dir, "static_requirement_matching.jsonl") if use_static else None
    dynamic_output_path = os.path.join(args.output_dir, "dynamic_requirement_matching.jsonl") if use_dynamic else None

    # 加载数据
    print("正在读取原始数据...")
    raw_data = load_jsonl_data(args.input_file)
    print(f"原始数据加载完成，共 {len(raw_data)} 条")

    # 按需加载模板
    static_template = load_prompt_template(args.static_template) if use_static else None
    dynamic_template = load_prompt_template(args.dynamic_template) if use_dynamic else None

    # 初始化结果列表
    static_items = []
    dynamic_items = []

    # 处理每一条数据
    print("正在生成匹配数据...")
    for item in tqdm(raw_data, desc="处理条目"):
        if use_static:
            static_items.append(generate_static_matching_item(item, static_template))
        if use_dynamic:
            dynamic_item = generate_dynamic_matching_item(item, dynamic_template)
            if dynamic_item is not None:
                dynamic_items.append(dynamic_item)

    # 按需保存
    if static_items:
        save_as_jsonl(static_items, static_output_path)
    if dynamic_items:
        save_as_jsonl(dynamic_items, dynamic_output_path)


if __name__ == "__main__":
    main()