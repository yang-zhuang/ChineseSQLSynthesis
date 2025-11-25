import json
import random
import argparse
from pathlib import Path

import re


def remove_sql_comments(sql: str) -> str:
    """
    移除 SQL 字符串中的注释：
      - 单行注释：以 '-- ' 开头（注意空格），直到行尾
      - 多行注释：/* ... */
    不会误删字符串中的 '--' 或 '/*'（通过简单启发式：仅处理非字符串上下文，此处为简化假设注释不嵌套在字符串中）
    """
    if not sql:
        return sql

    # Step 1: 移除多行注释 /* ... */
    # 使用非贪婪匹配，支持跨行
    sql_no_multiline = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    # Step 2: 移除单行注释 -- ...
    # 要求 '--' 后必须有空格或换行（符合 SQL 标准）
    # 注意：不能简单替换所有 '--'，因为可能出现在标识符或字符串中（如 'abc--def'）
    # 此处采用逐行处理更安全
    lines = sql_no_multiline.split('\n')
    cleaned_lines = []
    for line in lines:
        # 查找 '-- '（注意空格）的位置
        idx = line.find('--')
        if idx != -1:
            line = line[:idx]
        # 可选：进一步去除行尾空格
        cleaned_lines.append(line.rstrip())

    result = '\n'.join(cleaned_lines).strip()
    # 如果结果为空，返回空字符串而非 None
    return result if result else ''


def load_annotated_ddl(input_path: str):
    """从 JSONL 文件中加载带注释的 DDL 数据记录。"""
    annotated_records = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:  # 跳过空行
                annotated_records.append(json.loads(line))
    return annotated_records


def load_prompt_template(template_path: str) -> str:
    """从文本文件中读取提示模板。"""
    with open(template_path, encoding="utf-8") as f:
        return f.read().strip()


def build_conversations(annotated_records, prompt_template: str):
    """
    根据每条记录和提示模板，构造包含用户提示和真实 SQL 的对话数据。
    同时自动清理 ground_truth SQL 中的注释。

    返回格式为列表，每项包含：
      - prompt: 对话列表（当前仅用户消息）
      - ground_truth: 对应的真实 SQL 语句
    """
    conversations = []
    for record in annotated_records:
        # 提取元数据
        metadata = record["question_synthesis_metadata"]
        prompt_context = record["prompt_context"]["metadata"]

        engine = metadata["engine"]
        schema_desc = metadata["schema"]
        sample_data = prompt_context["db_value_prompt"]
        user_question = record["synthesis_question"]
        ground_truth_sql = metadata["sql"]

        # 🔥 新增：清理 SQL 中的注释
        clean_sql = remove_sql_comments(ground_truth_sql)

        # 填充模板
        formatted_prompt = (
            prompt_template
            .replace("{database_engine}", engine)
            .replace("{schema_description}", schema_desc)
            .replace("{sample_data}", json.dumps(sample_data, ensure_ascii=False, indent=2))
            .replace("{user_question}", user_question)
        )

        # 构造单条训练样本
        conversation = {
            "prompt": [{"role": "user", "content": formatted_prompt}],
            "ground_truth": clean_sql  # 使用清理后的 SQL
        }
        conversations.append(conversation)
    return conversations


def split_train_test(data, test_ratio=0.2, seed=42):
    """将数据按指定比例随机划分为训练集和测试集。"""
    random.seed(seed)
    random.shuffle(data)
    split_index = int(len(data) * (1 - test_ratio))
    return data[:split_index], data[split_index:]


def save_jsonl(data, output_path: str):
    """将数据列表保存为 JSONL 格式文件（每行一个 JSON 对象）。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)  # 自动创建输出目录
    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush()


def main():
    """主函数：解析参数、加载数据、生成样本、划分并保存结果。"""
    parser = argparse.ArgumentParser(description="生成用于 SQL 生成模型的训练与测试数据集")
    parser.add_argument(
        "--input-jsonl",
        type=str,
        default="../data_synthesis/sql_query_match_validation/output/final/static_requirement_matching/annotated_ddl.jsonl",
        help="输入的带注释 DDL 数据文件路径（JSONL 格式）"
    )
    parser.add_argument(
        "--prompt-template",
        type=str,
        default="prompts/sql_generation_prompt.txt",
        help="提示模板文件路径"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="../../data",
        help="输出目录，用于保存 train.jsonl 和 test.jsonl"
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.2,
        help="测试集占比，默认为 0.2（即 8:2 划分）"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子，确保数据划分可复现"
    )
    args = parser.parse_args()

    # 加载原始数据和提示模板
    annotated_ddl = load_annotated_ddl(args.input_jsonl)
    prompt_template = load_prompt_template(args.prompt_template)

    # 构建对话格式训练样本
    conversations = build_conversations(annotated_ddl, prompt_template)
    print(f"共生成样本数量: {len(conversations)}")

    # 划分训练集与测试集
    train_data, test_data = split_train_test(
        conversations,
        test_ratio=args.test_ratio,
        seed=args.seed
    )
    print(f"训练集样本数: {len(train_data)}，测试集样本数: {len(test_data)}")

    # 保存结果
    output_dir = Path(args.output_dir)
    save_jsonl(train_data, output_dir / "train.jsonl")
    save_jsonl(test_data, output_dir / "test.jsonl")

    print(f"训练和测试数据已保存至目录: {output_dir.resolve()}")


if __name__ == "__main__":
    main()