# find_similar_tables.py

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Final

from retrieve.vector_search_engine import VectorRetriever


# ✅ 定义全局常量：所有需要保留的元数据字段（不用于嵌入，但需随结果返回）
METADATA_FIELDS: Final[List[str]] = [
    "table_name",
    "create_sql",
    "sample_data",
    "annotated_ddl",
    "table_summary"  # 注意：这个字段名应与 --text_key 一致（默认为 "table_summary"）
]


def parse_args():
    """解析命令行参数。

    Returns:
        argparse.Namespace: 解析后的参数对象。
    """
    parser = argparse.ArgumentParser(
        description="基于表摘要向量化，检索每个表的相似表，并将结果附加到原始记录中"
    )
    parser.add_argument(
        "--input_file",
        type=str,
        default="../generate_table_summaries/output/final/annotated_ddl.jsonl",
        help="包含表摘要等信息的输入文件路径（JSONL 格式）"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="output/final/similarity_enhanced_tables.jsonl",
        help="输出文件路径，包含原始字段 + 相似表列表"
    )
    parser.add_argument(
        "--embed_model_path",
        type=str,
        default="/root/autodl-tmp/modelscope/nlp_gte_sentence-embedding_chinese-small",
        help="本地嵌入模型路径"
    )
    parser.add_argument(
        "--text_key",
        type=str,
        default="table_summary",
        help="用于生成向量的文本字段名（必须在 METADATA_FIELDS 中）"
    )
    parser.add_argument(
        "--similarity_top_k",
        type=int,
        default=5,
        help="检索返回的最相似结果数量"
    )
    parser.add_argument(
        "--similarity_cutoff",
        type=float,
        default=0.7,
        help="相似度阈值，低于此值的结果将被过滤"
    )
    parser.add_argument(
        "--use_milvus",
        action="store_true",
        help="是否使用 Milvus 作为向量数据库（默认使用内存索引）"
    )
    return parser.parse_args()


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """从 JSONL 文件中加载记录列表。

    Args:
        file_path (str): JSONL 文件路径。

    Returns:
        List[Dict[str, Any]]: 解析后的记录列表。
    """
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


def create_retriever(
    input_file: str,
    embed_model_path: str,
    text_key: str,
    use_milvus: bool,
    similarity_top_k: int,
    similarity_cutoff: float
) -> VectorRetriever:
    """初始化并返回配置好的向量检索器。

    Args:
        input_file (str): 输入数据文件路径。
        embed_model_path (str): 嵌入模型路径。
        text_key (str): 用于嵌入的文本字段名。
        use_milvus (bool): 是否使用 Milvus。
        similarity_top_k (int): 检索 Top-K 结果数。
        similarity_cutoff (float): 相似度阈值。

    Returns:
        VectorRetriever: 配置完成的检索器实例。
    """
    # 使用全局常量，但确保 text_key 在其中（可扩展性考虑）
    if text_key not in METADATA_FIELDS:
        raise ValueError(f"--text_key '{text_key}' 不在预定义的元数据字段中: {METADATA_FIELDS}")

    excluded_keys = ",".join(METADATA_FIELDS)
    retriever = VectorRetriever(
        config_prefix="TABLE_SUMMARY_",
        embed_model_path=embed_model_path,
        data_file=input_file,
        text_key=text_key,
        excluded_metadata_keys=excluded_keys,
        use_milvus=use_milvus,
        similarity_top_k=similarity_top_k,
        similarity_cutoff=similarity_cutoff,
    )
    return retriever


def enhance_records_with_similar_tables(
    records: List[Dict[str, Any]],
    retriever: VectorRetriever,
    text_key: str
) -> List[Dict[str, Any]]:
    """为每条记录检索相似表，并将结果附加到记录中。

    Args:
        records (List[Dict[str, Any]]): 原始记录列表。
        retriever (VectorRetriever): 已构建索引的检索器。
        text_key (str): 用于查询的文本字段名。

    Returns:
        List[Dict[str, Any]]: 增强后的记录列表，每条包含 'similar_tables' 字段。
    """
    enhanced = []
    for record in records:
        query_text = record.get(text_key)
        if not query_text or not isinstance(query_text, str):
            record["similar_tables"] = []
            enhanced.append(record)
            continue

        similar_nodes = retriever.retrieve(query_text=query_text)
        similar_tables = []

        for node in similar_nodes[1:]:
            meta = node.metadata
            # 使用常量字段列表过滤元数据
            filtered_meta = {key: meta.get(key) for key in METADATA_FIELDS if key in meta}
            similar_tables.append(filtered_meta)

        record["similar_tables"] = similar_tables
        enhanced.append(record)

    return enhanced


def save_jsonl(records: List[Dict[str, Any]], output_path: str):
    """将记录列表保存为 JSONL 文件。

    Args:
        records (List[Dict[str, Any]]): 要保存的记录列表。
        output_path (str): 输出文件路径。
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")
            f.flush()


def main():
    """主函数：协调整个相似表检索与增强流程。"""
    args = parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"正在加载数据: {input_path}")
    original_records = load_jsonl(args.input_file)
    print(f"共加载 {len(original_records)} 条表记录")

    print("正在初始化向量检索器...")
    retriever = create_retriever(
        input_file=args.input_file,
        embed_model_path=args.embed_model_path,
        text_key=args.text_key,
        use_milvus=args.use_milvus,
        similarity_top_k=args.similarity_top_k,
        similarity_cutoff=args.similarity_cutoff
    )

    print("正在构建向量索引...")
    retriever.build_index()
    print("✅ 向量索引构建完成")

    print("正在检索相似表...")
    enhanced_records = enhance_records_with_similar_tables(
        records=original_records,
        retriever=retriever,
        text_key=args.text_key
    )

    print("正在保存结果...")
    save_jsonl(enhanced_records, str(output_path))

    print(f"/n✅ 相似表检索与增强完成！")
    print(f"  输入记录数: {len(original_records)}")
    print(f"  输出文件: {output_path}")


if __name__ == "__main__":
    main()