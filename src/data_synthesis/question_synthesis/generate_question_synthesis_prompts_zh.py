import json
import os
import random
import argparse
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm

# ==================== 常量配置（集中管理，便于维护）====================
SUPPORTED_STYLES = [
    "Formal", "Colloquial", "Imperative", "Interrogative",
    "Descriptive", "Concise", "Vague", "Metaphorical", "Multi-turn Dialogue"
]

# 模板文件映射（避免硬编码分散）
TEMPLATE_CONFIG = {
    "main": "question_synthesis_prompt_zh.txt",
    "type_templates": {
        "w_ek": {
            "steps": "steps_w_ek_zh.txt",
            "guidelines": "guidelines_w_ek_zh.txt",
            "instruction": "instruction_wo_ek_zh.txt",
            "output_format": "output_format_w_ek_zh.txt"
        },
        "multi_round": {
            "steps": "steps_multi_round_zh.txt",
            "guidelines": "guidelines_multi_round_zh.txt",
            "instruction": "instruction_multi_round_zh.txt",
            "output_format": "output_format_multi_round_zh.txt"
        },
        "wo_ek": {
            "steps": "steps_wo_ek_zh.txt",
            "guidelines": "guidelines_wo_ek_zh.txt",
            "instruction": "instruction_wo_ek_zh.txt",
            "output_format": "output_format_wo_ek_zh.txt"
        }
    },
    "style_templates": {style: f"style_for_{style.replace(' ', '_')}.txt" for style in SUPPORTED_STYLES}
}


# ==================== 工具函数（单一职责，可复用）====================

def load_jsonl_file(file_path: str) -> List[Dict]:
    """
    从 JSONL 文件中读取数据，每行一个 JSON 对象。

    Args:
        file_path: 输入文件路径

    Returns:
        解析后的字典列表
    """
    data_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data_list.append(json.loads(line))
    except Exception as e:
        raise RuntimeError(f"读取 JSONL 文件失败 ({file_path}): {e}")
    return data_list

def load_jsonl_files(file_paths: List[str]) -> List[Dict]:
    """
    从多个 JSONL 文件中读取数据并合并。

    Args:
        file_paths: 输入文件路径列表

    Returns:
        合并后的字典列表
    """
    all_data = []
    for file_path in file_paths:
        print(f"📥 正在加载文件: {file_path}")
        file_data = load_jsonl_file(file_path)
        all_data.extend(file_data)
        print(f"   ✅ 成功加载 {len(file_data)} 条数据")
    return all_data

def load_prompt_templates(template_dir: str) -> Tuple[str, Dict[str, Dict[str, str]], Dict[str, str]]:
    """
    加载所有 Prompt 模板文件（主模板、类型模板、风格模板）。

    Args:
        template_dir: 模板文件所在目录

    Returns:
        (主模板内容, 类型模板字典, 风格描述字典)
    """
    # 加载主模板
    main_template_path = os.path.join(template_dir, TEMPLATE_CONFIG["main"])
    with open(main_template_path, "r", encoding="utf-8") as f:
        main_template = f.read()

    # 加载类型模板
    type_templates = {}
    for template_type, file_map in TEMPLATE_CONFIG["type_templates"].items():
        type_templates[template_type] = {}
        for key, filename in file_map.items():
            file_path = os.path.join(template_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                type_templates[template_type][key] = f.read().strip()

    # 加载风格描述模板
    style_descriptions = {}
    for style, filename in TEMPLATE_CONFIG["style_templates"].items():
        file_path = os.path.join(template_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            style_descriptions[style] = f.read().strip()

    return main_template, type_templates, style_descriptions


def select_template_by_style(style_name: str, type_templates: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """
    根据问题风格选择对应的 Prompt 类型模板。

    Args:
        style_name: 风格名称
        type_templates: 所有类型模板

    Returns:
        选中的模板字典
    """
    if style_name in {"Vague", "Metaphorical"}:
        return type_templates["w_ek"]
    elif style_name == "Multi-turn Dialogue":
        return type_templates["multi_round"]
    else:
        return type_templates["wo_ek"]


def generate_prompt_for_item(
        sql_item: Dict,
        main_template: str,
        type_templates: Dict[str, Dict[str, str]],
        style_descriptions: Dict[str, str],
        sql_engine: str
) -> Optional[Dict]:
    """
    为单个 SQL 条目生成问题合成 Prompt。

    Args:
        sql_item: 原始 SQL 数据项
        main_template: 主 Prompt 模板
        type_templates: 类型模板字典
        style_descriptions: 风格描述字典
        sql_engine: SQL 引擎类型（如 'doris', 'sqlite', 'mysql'）

    Returns:
        添加了 prompt 元数据的 sql_item，或 None（如数据异常）
    """
    try:
        metadata = sql_item['prompt_context']['metadata']
        schema_str = metadata['schema_str']
        if isinstance(schema_str, list):
            schema_str = "\n\n".join(schema_str)

        # 随机选择风格
        selected_style = random.choice(SUPPORTED_STYLES)
        style_desc = style_descriptions[selected_style]
        selected_type_template = select_template_by_style(selected_style, type_templates)

        # 填充主模板
        filled_prompt = main_template.format(
            style_desc=style_desc,
            engine=sql_engine,
            schema=schema_str,
            sql=sql_item['synthesis_sql'],
            steps=selected_type_template["steps"],
            guidelines=selected_type_template["guidelines"],
            output_format=selected_type_template["output_format"],
            instruction=selected_type_template["instruction"],
        )

        # 注入元数据
        sql_item["question_synthesis_metadata"] = {
            "prompt": filled_prompt,
            "style": selected_style,
            "style_description": style_desc,
            "engine": sql_engine,
            "sql": sql_item['synthesis_sql'],
            "schema": schema_str,
            "steps": selected_type_template["steps"],
            "guidelines": selected_type_template["guidelines"],
            "output_format": selected_type_template["output_format"],
            "instruction": selected_type_template["instruction"],
        }
        return sql_item

    except KeyError as e:
        print(f"⚠️ 跳过无效数据项（缺少字段: {e}）")
        return None
    except Exception as e:
        print(f"⚠️ 生成 Prompt 时出错: {e}")
        return None


def write_jsonl_file(data: List[Dict], output_path: str) -> None:
    """
    将数据写入 JSONL 文件（每行一个 JSON 对象）。

    Args:
        data: 要写入的数据列表
        output_path: 输出文件路径
    """
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ==================== 命令行参数解析 ====================

def parse_arguments() -> argparse.Namespace:
    """解析命令行参数，支持灵活配置，并提供合理的默认值。"""
    parser = argparse.ArgumentParser(description="生成 SQL 对应的问题合成 Prompt")

    parser.add_argument(
        "--input-files",
        nargs='+',  # 支持多个文件
        type=str,
        default=["../sql_synthesis/output/final/annotated_ddl.jsonl", "../sql_correction/output/final/annotated_ddl.jsonl"],
        help="输入的 SQL 合成结果文件路径（JSONL 格式，可指定多个，默认: ../sql_synthesis/output/final/annotated_ddl.jsonl）"
    )
    parser.add_argument(
        "--template-dir",
        type=str,
        default="./prompts",
        help="Prompt 模板目录（默认: ./prompts）"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="output/prompt/generated_prompts.jsonl",
        help="输出文件路径（JSONL 格式，默认: output/prompts/question_synthesis_prompts_zh.jsonl）"
    )
    parser.add_argument(
        "--sql-engine",
        type=str,
        default="sqlite",
        choices=["sqlite", "mysql", "postgresql", "doris", "clickhouse", "others"],
        help="目标 SQL 引擎类型（影响模板中的 engine 字段，默认: doris）"
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="随机种子，用于风格选择的可复现性（默认: 42）"
    )

    return parser.parse_args()


# ==================== 主函数 ====================

def main():
    args = parse_arguments()
    random.seed(args.random_seed)

    print("=" * 60)
    print("📥 正在加载输入数据...")
    sql_data_list = load_jsonl_files(args.input_files)  # 修改为加载多个文件
    print(f"✅ 成功加载 {len(sql_data_list)} 条 SQL 数据")

    print("\n📥 正在加载 Prompt 模板...")
    main_tmpl, type_tmpls, style_descs = load_prompt_templates(args.template_dir)
    print("✅ 模板加载完成")

    print("\n🚀 开始生成问题合成 Prompt...")
    generated_items = []
    for item in tqdm(sql_data_list, desc="生成 Prompt"):
        result = generate_prompt_for_item(
            sql_item=item,
            main_template=main_tmpl,
            type_templates=type_tmpls,
            style_descriptions=style_descs,
            sql_engine=args.sql_engine
        )
        if result is not None:
            generated_items.append(result)

    print(f"✅ 成功生成 {len(generated_items)} 个有效 Prompt")

    print(f"\n💾 正在保存结果到: {args.output_file}")
    write_jsonl_file(generated_items, args.output_file)
    print("✅ 保存完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()