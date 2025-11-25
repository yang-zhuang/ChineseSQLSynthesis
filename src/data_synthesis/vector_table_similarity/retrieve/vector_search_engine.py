import json
import os
from typing import Any, List, Optional, cast
from transformers import AutoTokenizer
from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.settings import Settings
from llama_index.core.vector_stores.simple import SimpleVectorStore
from llama_index.core.vector_stores.types import (
    VectorStoreQuery,
    VectorStoreQueryMode,
    VectorStoreQueryResult,
)
from llama_index.core.indices.query.embedding_utils import (
    get_top_k_embeddings,
    get_top_k_embeddings_learner,
    get_top_k_mmr_embeddings,
)
from llama_index.core.vector_stores.utils import build_metadata_filter_fn
from llama_index.core.indices.vector_store.retrievers import VectorIndexRetriever
import logging
from llama_index.vector_stores.milvus import MilvusVectorStore
import sys

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# 尝试导入 HuggingFaceLocalEmbeddings（处理不同导入路径）
try:
    # 尝试从项目结构中导入
    from vector.huggingface_embeddings import HuggingFaceLocalEmbeddings
except ImportError:
    try:
        # 尝试从当前目录导入
        from .vector.huggingface_embeddings import HuggingFaceLocalEmbeddings
    except (ImportError, ValueError):
        # 最后尝试动态添加路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)  # 假设项目根目录是父目录
        sys.path.append(project_root)
        try:
            from vector.huggingface_embeddings import HuggingFaceLocalEmbeddings
        except ImportError:
            logger.error("无法导入 HuggingFaceLocalEmbeddings，请确保模块路径正确")
            raise

# 支持的机器学习检索模式集合
LEARNER_MODES = {
    VectorStoreQueryMode.SVM,
    VectorStoreQueryMode.LINEAR_REGRESSION,
    VectorStoreQueryMode.LOGISTIC_REGRESSION,
}
MMR_MODE = VectorStoreQueryMode.MMR

class CustomSimpleVectorStore(SimpleVectorStore):
    """自定义简单向量存储实现，扩展基础查询逻辑。

    继承自 llama_index 的 SimpleVectorStore，支持多种检索模式（默认相似性、
    机器学习模型、MMR），并增强了元数据过滤的校验逻辑。
    """

    def query(
        self,
        query: VectorStoreQuery,
        **kwargs: Any,
    ) -> VectorStoreQueryResult:
        """查询向量存储，返回符合条件的Top-K结果。

        根据查询向量和检索模式，从存储中筛选出最相似的节点，并返回其ID和相似度分数。
        支持元数据过滤和节点ID过滤，不同模式下的检索逻辑不同。

        Args:
            query: 向量存储查询对象，包含查询向量、检索模式、过滤条件等信息。
            **kwargs: 额外检索参数，不同模式下支持的参数不同：
                - 当模式为 DEFAULT 时，支持 similarity_cutoff（相似度阈值，默认0.8）；
                - 当模式为 MMR 时，支持 mmr_threshold（MMR阈值）。

        Returns:
            VectorStoreQueryResult: 检索结果对象，包含匹配节点的ID列表和对应的相似度分数列表。

        Raises:
            ValueError: 当查询包含元数据过滤条件，但存储中未包含元数据时触发；
                或当传入不支持的检索模式时触发。
        """
        # 元数据过滤校验：若查询有过滤条件，但存储无元数据，则无法过滤
        if (
            query.filters is not None
            and self.data.embedding_dict
            and not self.data.metadata_dict
        ):
            raise ValueError(
                "无法对无元数据的存储进行过滤，请重建包含元数据的存储"
            )

        # 构建元数据过滤函数（基于查询中的filters）
        query_filter_fn = build_metadata_filter_fn(
            lambda node_id: self.data.metadata_dict[node_id], query.filters
        )

        # 构建节点ID过滤函数（若指定了node_ids，则仅保留这些ID）
        if query.node_ids is not None:
            available_ids = set(query.node_ids)
            node_filter_fn = lambda node_id: node_id in available_ids
        else:
            node_filter_fn = lambda node_id: True  # 无过滤，全部保留

        # 收集符合过滤条件的节点ID和对应的嵌入向量
        node_ids: List[str] = []
        embeddings: List[List[float]] = []
        for node_id, embedding in self.data.embedding_dict.items():
            if node_filter_fn(node_id) and query_filter_fn(node_id):
                node_ids.append(node_id)
                embeddings.append(embedding)

        # 类型转换：确保查询向量为List[float]
        query_embedding = cast(List[float], query.query_embedding)

        # 根据检索模式执行不同的相似性计算逻辑
        if query.mode in LEARNER_MODES:
            # 机器学习模型模式（SVM/线性回归/逻辑回归）
            top_similarities, top_ids = get_top_k_embeddings_learner(
                query_embedding,
                embeddings,
                similarity_top_k=query.similarity_top_k,
                embedding_ids=node_ids,
            )
        elif query.mode == MMR_MODE:
            # MMR（最大边际相关性）模式
            mmr_threshold = kwargs.get("mmr_threshold")
            top_similarities, top_ids = get_top_k_mmr_embeddings(
                query_embedding,
                embeddings,
                similarity_top_k=query.similarity_top_k,
                embedding_ids=node_ids,
                mmr_threshold=mmr_threshold,
            )
        elif query.mode == VectorStoreQueryMode.DEFAULT:
            # 默认相似性检索模式
            top_similarities, top_ids = get_top_k_embeddings(
                query_embedding,
                embeddings,
                similarity_top_k=query.similarity_top_k,
                embedding_ids=node_ids,
                similarity_cutoff=kwargs.get("similarity_cutoff", 0.8),
            )
        else:
            raise ValueError(f"不支持的检索模式: {query.mode}")

        return VectorStoreQueryResult(
            similarities=top_similarities,
            ids=top_ids,
        )

class VectorRetriever:
    """通用向量检索器，支持多实例化，通过配置前缀区分不同场景"""

    def __init__(
        self,
        config_prefix: str,
        # 以下为所有可配置参数，通过__init__传入
        embed_model_path: str = "./modelscope/nlp_gte_sentence-embedding_chinese-small",
        embedding_dim: int = 512,
        data_file: str = "table_metadata_comment_summary.jsonl",
        text_key: str | List[str] = "summary",
        excluded_metadata_keys: str | List[str] = "",
        use_milvus: bool = False,
        milvus_uri: str = "./milvus_table_summary.db",
        milvus_similarity_metric: str = "cosine",
        insert_batch_size: int = 128,
        chunk_size: int = 10000000,
        similarity_top_k: int = 5,
        similarity_cutoff: float = 0.7
    ):
        """
        初始化向量检索器（多实例版本）

        Args:
            config_prefix: 环境变量配置前缀（如"TABLE_SUMMARY_"、"COLUMN_DESC_"），
                用于区分不同场景的配置（仅用于日志标识）
            embed_model_path: 嵌入模型路径
            embedding_dim: 嵌入维度
            data_file: 数据文件路径
            text_key: 从JSON中提取文本的键（支持单个字符串或列表）
            excluded_metadata_keys: 排除的元数据字段（支持单个字符串或列表）
            use_milvus: 是否使用Milvus
            milvus_uri: Milvus数据库路径
            milvus_similarity_metric: 相似度计算方式
            insert_batch_size: 批量插入大小
            chunk_size: 文本分块大小
            similarity_top_k: 检索返回的Top-K数量
            similarity_cutoff: 相似度阈值
        """
        self.config_prefix = config_prefix
        self.embed_model_path = embed_model_path
        self.embedding_dim = embedding_dim
        self.data_file = data_file
        self.text_key = [text_key] if isinstance(text_key, str) else text_key

        if isinstance(excluded_metadata_keys, str):
            self.excluded_metadata_keys = excluded_metadata_keys.split(",")
        else:
            self.excluded_metadata_keys = excluded_metadata_keys

        self.use_milvus = use_milvus
        self.milvus_uri = milvus_uri
        self.milvus_similarity_metric = milvus_similarity_metric
        self.insert_batch_size = insert_batch_size
        self.chunk_size = chunk_size
        self.similarity_top_k = similarity_top_k
        self.similarity_cutoff = similarity_cutoff

        # 初始化组件
        self.documents: List[Document] = []
        self.vector_store: Any = None
        self.storage_context: Optional[StorageContext] = None
        self.index: Optional[VectorStoreIndex] = None
        self.embed_model: Any = None
        self._index_built = False

        # 初始化嵌入模型
        self._init_embed_model()
        Settings.embed_model = self.embed_model

    def _init_embed_model(self) -> None:
        """初始化嵌入模型"""
        try:
            AutoTokenizer.from_pretrained(self.embed_model_path)
            self.embed_model = HuggingFaceLocalEmbeddings(
                model_path=self.embed_model_path,
                device=None
            )
            logger.info(f"[{self.config_prefix}] 嵌入模型初始化成功（路径：{self.embed_model_path}）")
        except Exception as e:
            raise RuntimeError(f"[{self.config_prefix}] 嵌入模型初始化失败：{str(e)}")

    def _load_documents(self) -> None:
        """加载当前场景的文档"""
        if not os.path.exists(self.data_file):
            raise FileNotFoundError(f"[{self.config_prefix}] 数据集文件不存在: {self.data_file}")

        self.documents = []
        with open(self.data_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line)
                    text = data
                    for key in self.text_key:
                        text = text[key]
                    if not isinstance(text, str):
                        raise ValueError(f"提取的文本不是字符串类型（值：{text}）")

                    doc = Document(
                        text=text,
                        metadata=data.copy()
                    )
                    doc.excluded_embed_metadata_keys = self.excluded_metadata_keys
                    self.documents.append(doc)
                except Exception as e:
                    logger.warning(f"[{self.config_prefix}] 处理第{line_num}行数据失败: {str(e)}，已跳过")

        logger.info(f"[{self.config_prefix}] 文档加载完成，共{len(self.documents)}个有效文档")

    def build_index(self, overwrite: bool = False) -> None:
        """构建当前场景的索引（仅首次或强制覆盖时执行）"""
        if self._index_built and not overwrite:
            logger.info(f"[{self.config_prefix}] 索引已构建，无需重复执行")
            return

        self._load_documents()

        # 初始化向量存储
        if self.use_milvus:
            self.vector_store = MilvusVectorStore(
                uri=self.milvus_uri,
                dim=self.embedding_dim,
                overwrite=overwrite,
                similarity_metric=self.milvus_similarity_metric
            )
            logger.info(f"[{self.config_prefix}] 初始化Milvus存储（路径：{self.milvus_uri}）")
        else:
            self.vector_store = CustomSimpleVectorStore()
            logger.info(f"[{self.config_prefix}] 初始化自定义简单存储")

        # 创建索引
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_documents(
            self.documents,
            storage_context=self.storage_context,
            transformations=[SentenceSplitter(chunk_size=self.chunk_size)],
            embed_model=self.embed_model,
            insert_batch_size=self.insert_batch_size,
            show_progress=True,
        )

        self._index_built = True
        logger.info(f"[{self.config_prefix}] 索引构建完成")

    def retrieve(
        self,
        query_text: str,
        similarity_top_k: Optional[int] = None,
        similarity_cutoff: Optional[float] = None,
        **kwargs: Any
    ) -> List[Any]:
        """检索当前场景的相似节点"""
        if not self._index_built:
            raise RuntimeError(f"[{self.config_prefix}] 索引未构建，请先调用build_index()")

        top_k = similarity_top_k or self.similarity_top_k
        cutoff = similarity_cutoff or self.similarity_cutoff

        retriever = VectorIndexRetriever(
            index=self.index,
            callback_manager=self.index._callback_manager,
            object_map=self.index._object_map,
            similarity_top_k=top_k,
            vector_store_kwargs={'similarity_cutoff': cutoff, **kwargs}
        )

        nodes = retriever.retrieve(query_text)
        logger.info(f"[{self.config_prefix}] 检索完成，返回{len(nodes)}个节点（Top-{top_k}）")
        return nodes


# 示例用法
if __name__ == "__main__":
    # 实例化不同场景的检索器（其他模块可直接导入使用）
    table_summary_retriever = VectorRetriever(
        config_prefix="TABLE_SUMMARY_",
        embed_model_path="D:/modelscope/nlp_gte_sentence-embedding_chinese-small",
        data_file=r"D:\Code\text2sql生成\为数据库中的表生成总结信息\output\final\annotated_ddl.jsonl",
        text_key="table_summary",
        excluded_metadata_keys="table_name,create_sql,sample_data,annotated_ddl,table_summary",
        use_milvus=False,
        similarity_top_k=50,
        similarity_cutoff=0.7
    )

    # column_desc_retriever = VectorRetriever(
    #     config_prefix="COLUMN_DESC_",
    #     embed_model_path="./modelscope/nlp_gte_sentence-embedding_chinese-small",
    #     data_file="column_descriptions.jsonl",
    #     text_key="description",
    #     excluded_metadata_keys=["column_name", "table_name"],
    #     use_milvus=True,
    #     milvus_uri="./milvus_column_desc.db",
    #     similarity_top_k=10
    # )

    # 构建索引（首次运行或数据更新时执行一次）
    table_summary_retriever.build_index()

    # 执行检索（使用传入的配置参数）
    query = "零售门店的核心运营数据"
    similar_nodes = table_summary_retriever.retrieve(query_text=query)

    # 输出结果
    for i, node in enumerate(similar_nodes, 1):
        print(f"\n{'='*20} 结果{i} {'='*20}")
        print(f"相似度分数: {node.score:.4f}")
        print(f"文本内容: {node.text[:500]}...")