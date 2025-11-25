import json
import os
from typing import Any, List, Optional, cast
from dotenv import load_dotenv  # 需安装：pip install python-dotenv
from transformers import AutoTokenizer
from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.settings import Settings
from llama_index.core.vector_stores.simple import SimpleVectorStore
from llama_index.vector_stores.milvus import MilvusVectorStore
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
from ..vector.huggingface_embeddings import HuggingFaceLocalEmbeddings
import logging

# 加载.env文件中的环境变量
load_dotenv()  # 自动查找项目根目录的.env文件

# # 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# 常量定义
LEARNER_MODES = {
    VectorStoreQueryMode.SVM,
    VectorStoreQueryMode.LINEAR_REGRESSION,
    VectorStoreQueryMode.LOGISTIC_REGRESSION,
}
"""支持的机器学习检索模式集合"""

MMR_MODE = VectorStoreQueryMode.MMR
"""MMR（最大边际相关性）检索模式"""


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

    def __init__(self, config_prefix: str):
        """
        初始化向量检索器（多实例版本）

        Args:
            config_prefix: 环境变量配置前缀（如"TABLE_SUMMARY_"、"COLUMN_DESC_"），
                用于区分不同场景的配置
        """
        self.config_prefix = config_prefix  # 配置前缀（核心：通过它读取不同场景的环境变量）
        self._index_built = False  # 标记索引是否已构建

        # 从环境变量读取配置（使用前缀拼接）
        self._load_configs()

        # 初始化组件
        self.documents: List[Document] = []
        self.vector_store: Any = None
        self.storage_context: Optional[StorageContext] = None
        self.index: Optional[VectorStoreIndex] = None
        self.embed_model: Any = None

        # 初始化嵌入模型
        self._init_embed_model()
        Settings.embed_model = self.embed_model

    def get_prefix_with_target(self, target="performance"):
        # 1. 获取当前文件的绝对路径（系统原生格式）
        abs_path = os.path.abspath(__file__)
        # 2. 规范化路径（处理相对路径符号，统一分隔符）
        norm_path = os.path.normpath(abs_path)
        # 3. 按系统分隔符拆分组件（保留所有原生结构，包括空字符串）
        path_parts = norm_path.split(os.sep)

        try:
            target_index = path_parts.index(target)
        except ValueError:
            return None  # 未找到目标

        # 4. 截取前缀组件（包含目标）
        prefix_parts = path_parts[:target_index + 1]
        # 5. 用系统分隔符直接拼接组件（核心改进）
        prefix_path = os.sep.join(prefix_parts)

        return prefix_path

    def _load_configs(self) -> None:
        """根据配置前缀加载环境变量"""
        # 通用配置（无前缀）
        self.embed_model_path = os.getenv("EMBED_MODEL_PATH", "./modelscope/nlp_gte_sentence-embedding_chinese-small")
        self.embedding_dim = int(os.getenv("EMBEDDING_DIM", "512"))

        prefix_path = self.get_prefix_with_target('text2sql_evaluator')

        # 场景专用配置（带前缀）
        data_file_name = os.getenv(f"{self.config_prefix}DATA_FILE", f"{self.config_prefix.lower()}data.jsonl")

        self.data_file = os.path.join(prefix_path, 'toolkit', 'database' , data_file_name)

        self.text_key = os.getenv(f"{self.config_prefix}TEXT_KEY", "summary").split(",")
        self.excluded_metadata_keys = os.getenv(
            f"{self.config_prefix}EXCLUDED_METADATA_KEYS", ""
        ).split(",")

        # 存储配置
        self.use_milvus = os.getenv(f"{self.config_prefix}USE_MILVUS", "False").lower() == "true"
        self.milvus_uri = os.getenv(f"{self.config_prefix}MILVUS_URI", f"./milvus_{self.config_prefix.lower()}.db")
        self.milvus_similarity_metric = os.getenv(f"{self.config_prefix}MILVUS_SIMILARITY_METRIC", "cosine")

        # 索引配置
        self.insert_batch_size = int(os.getenv(f"{self.config_prefix}INSERT_BATCH_SIZE", "128"))
        self.chunk_size = int(os.getenv(f"{self.config_prefix}CHUNK_SIZE", "10000000"))

        # 检索配置
        self.similarity_top_k = int(os.getenv(f"{self.config_prefix}SIMILARITY_TOP_K", "5"))
        self.similarity_cutoff = float(os.getenv(f"{self.config_prefix}SIMILARITY_CUTOFF", "0.7"))

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

    # @timer
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

    # @timer
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
            vector_store_kwargs={'similarity_cutoff': cutoff,** kwargs}
        )

        nodes = retriever.retrieve(query_text)
        logger.info(f"[{self.config_prefix}] 检索完成，返回{len(nodes)}个节点（Top-{top_k}）")
        return nodes


# 实例化不同场景的检索器（其他模块可直接导入使用）
table_summary_retriever = VectorRetriever(config_prefix="TABLE_SUMMARY_")
column_desc_retriever = VectorRetriever(config_prefix="COLUMN_DESC_")


# 示例用法
if __name__ == "__main__":
    # 构建索引（首次运行或数据更新时执行一次）
    table_summary_retriever.build_index()

    # 执行检索（使用环境变量配置的默认参数）
    query = "Who is Paul Graham?"
    similar_nodes = table_summary_retriever.retrieve(query_text=query)

    # 输出结果
    for i, node in enumerate(similar_nodes, 1):
        print(f"\n{'='*20} 结果{i} {'='*20}")
        print(f"相似度分数: {node.score:.4f}")
        print(f"文本内容: {node.text[:500]}...")  # 仅显示前500字符