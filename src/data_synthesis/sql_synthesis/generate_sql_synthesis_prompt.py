import copy
import json
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from tqdm import tqdm


def safe_random_sample(lst, min_count, max_count):
    """在指定范围内安全地从列表中随机采样"""
    if not lst:
        return []
    max_count = min(max_count, len(lst))
    min_count = min(min_count, max_count)
    if min_count < 0:
        min_count = 0
    count = random.randint(min_count, max_count)
    return random.sample(lst, count)


def load_prompt_templates(
    main_template_path: Path,
    sql_func_template_path: Path,
    criteria_template_paths: Dict[str, Path]
) -> Dict[str, Any]:
    """加载所有提示模板到内存"""
    templates = {
        "main": main_template_path.read_text(encoding="utf-8"),
        "sql_func": sql_func_template_path.read_text(encoding="utf-8"),
        "criteria": {
            level: path.read_text(encoding="utf-8").strip()
            for level, path in criteria_template_paths.items()
        }
    }
    return templates


def generate_prompted_samples(
    annotated_data: List[Dict[str, Any]],
    templates: Dict[str, Any],
    similar_table_min: int,
    similar_table_max: int,
    available_func_min: int,
    available_func_max: int,
    prompts_per_item: int,
    db_engine: str
) -> List[Dict[str, Any]]:
    """为每条结构化数据生成多个带上下文的提示样本"""
    generated_samples = []
    complexity_levels = list(templates["criteria"].keys())
    prompt_id = 0

    for data in tqdm(annotated_data, desc="Generating prompts"):
        for _ in range(prompts_per_item):
            complexity = random.choice(complexity_levels)

            # 采样相似表（用于多表上下文）
            similar_tables = data.get("similar_tables", [])
            sampled_similar = safe_random_sample(
                similar_tables, similar_table_min, similar_table_max
            )

            # 构建 schema 字符串列表（主表 + 相似表）
            schemas = [data["annotated_ddl"]]
            schemas.extend(item["annotated_ddl"] for item in sampled_similar)

            # 构建样例数据（每个表取前2行）
            sample_data = {data["table_name"]: data["sample_data"][:2]}
            for item in sampled_similar:
                sample_data[item["table_name"]] = item["sample_data"][:2]

            # 构建可用函数列表（带中文说明）
            available_functions = []
            for func_name, description in data.get("function_descriptions", {}).items():
                available_functions.append({
                    "函数名称": func_name,
                    "函数说明": description
                })

            # 生成 SQL 函数提示片段
            sampled_funcs = []
            if not available_functions:
                sql_func_prompt = "**SQL 函数**\n你可以使用数据库引擎所支持的任何函数。\n"
            else:
                sampled_funcs = safe_random_sample(
                    available_functions, available_func_min, available_func_max
                )
                func_json_str = json.dumps(sampled_funcs, ensure_ascii=False, indent=2)
                sql_func_prompt = templates["sql_func"].replace("{sql_funcs}", func_json_str)

            # 使用几何分布生成目标列数（模拟真实查询复杂度）
            target_column_count = int(np.random.geometric(p=0.6))

            # 填充主提示模板
            final_prompt = (
                templates["main"]
                .replace("{schema_str}", "\n\n".join(schemas))
                .replace("{sql_function_prompt}", sql_func_prompt)
                .replace("{db_value_prompt}", json.dumps(sample_data, ensure_ascii=False, indent=2))
                .replace("{complexity}", complexity)
                .replace("{criterion}", templates["criteria"][complexity])
                .replace("{db_engine}", db_engine)
                .replace("{column_count}", str(target_column_count))
            )

            # 构建输出记录
            output_record = copy.deepcopy(data)
            output_record["prompt_context"] = {"filled": final_prompt}
            output_record["prompt_context"]['metadata'] = {
                'schema_str': schemas,
                'sql_func_prompt': sampled_funcs,
                'db_value_prompt': sample_data,
            }

            output_record["prompt_id"] = prompt_id

            prompt_id += 1

            generated_samples.append(output_record)

    return generated_samples


def load_annotated_data(input_path: Path) -> List[Dict[str, Any]]:
    """从 JSONL 文件加载标注后的 DDL 数据"""
    data_list = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data_list.append(json.loads(line))
    return data_list

def save_generated_prompts(output_path: Path, samples: List[Dict[str, Any]]):
    """将生成的提示样本保存为 JSONL 文件"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False))
            f.write("\n")

def parse_arguments():
    parser = argparse.ArgumentParser(description="基于结构化 DDL 生成 SQL 合成提示样本")

    # 输入输出路径
    parser.add_argument(
        "--input_file",
        type=str,
        default="../match_sqlite_functions/output/final/annotated_ddl.jsonl",
        help="输入的标注 DDL 数据文件（JSONL 格式）"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="./output/prompt/generated_prompts.jsonl",
        help="输出的提示样本文件路径"
    )

    # 模板路径
    parser.add_argument("--main_prompt", type=str, default="./prompts/sql_synthesis_prompt_zh.txt")
    parser.add_argument("--sql_func_prompt", type=str, default="./prompts/sql_func_template_zh.txt")
    parser.add_argument("--simple_criterion", type=str, default="prompts/criterion_for_simple_zh.txt")
    parser.add_argument("--moderate_criterion", type=str, default="prompts/criterion_for_moderate_zh.txt")
    parser.add_argument("--complex_criterion", type=str, default="prompts/criterion_for_complex_zh.txt")
    parser.add_argument("--highly_complex_criterion", type=str, default="prompts/criterion_for_highly_complex_zh.txt")

    # 采样参数
    parser.add_argument("--similar_table_min", type=int, default=1, help="相似表最小采样数量")
    parser.add_argument("--similar_table_max", type=int, default=3, help="相似表最大采样数量")
    parser.add_argument("--available_func_min", type=int, default=4, help="函数提示最小展示数量")
    parser.add_argument("--available_func_max", type=int, default=10, help="函数提示最大展示数量")
    parser.add_argument("--prompts_per_item", type=int, default=20, help="每条数据生成的提示数量")

    # 数据库引擎
    parser.add_argument("--db_engine", type=str, default="sqlite", choices=["sqlite", "mysql", "postgresql"], help="目标数据库引擎")

    return parser.parse_args()

def main():
    args = parse_arguments()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    # 加载数据
    annotated_data = load_annotated_data(input_path)
    print(f"成功加载 {len(annotated_data)} 条标注数据")

    # 构建 criteria 路径映射
    criteria_paths = {
        "Simple": Path(args.simple_criterion),
        "Moderate": Path(args.moderate_criterion),
        # "Complex": Path(args.complex_criterion),
        # "Highly Complex": Path(args.highly_complex_criterion),
    }

    # 验证模板文件是否存在
    all_template_paths = [
        Path(args.main_prompt),
        Path(args.sql_func_prompt),
        *criteria_paths.values()
    ]
    for p in all_template_paths:
        if not p.exists():
            raise FileNotFoundError(f"提示模板文件不存在: {p}")

    # 加载模板
    templates = load_prompt_templates(
        main_template_path=Path(args.main_prompt),
        sql_func_template_path=Path(args.sql_func_prompt),
        criteria_template_paths=criteria_paths
    )

    # 生成提示样本
    generated_samples = generate_prompted_samples(
        annotated_data=annotated_data,
        templates=templates,
        similar_table_min=args.similar_table_min,
        similar_table_max=args.similar_table_max,
        available_func_min=args.available_func_min,
        available_func_max=args.available_func_max,
        prompts_per_item=args.prompts_per_item,
        db_engine=args.db_engine
    )

    print(f"共生成 {len(generated_samples)} 个提示样本")

    random.seed(42)
    random.shuffle(generated_samples)
    # 保存结果
    save_generated_prompts(output_path, generated_samples)
    print(f"✅ 提示样本已保存至: {output_path}")


if __name__ == "__main__":
    main()
