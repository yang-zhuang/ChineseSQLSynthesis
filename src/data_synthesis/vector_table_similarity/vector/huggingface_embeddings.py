from typing import List, Any
from llama_index.core.embeddings import BaseEmbedding
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel


class HuggingFaceLocalEmbeddings(BaseEmbedding):
    """使用 HuggingFace Transformers 的本地嵌入模型"""

    def __init__(
            self,
            model_path: str = "D:\\modelscope\\nlp_gte_sentence-embedding_chinese-small",
            batch_size: int = 32,
            device: str = None,
            normalize_embeddings: bool = True,
            **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self._model_path = model_path
        self._batch_size = batch_size
        self._normalize_embeddings = normalize_embeddings

        # 自动选择设备
        if device is None:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self._device = device

        # 加载模型和分词器
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._model = AutoModel.from_pretrained(model_path).to(self._device)
        self._model.eval()

        print(f"Loaded embedding model from {model_path} on device: {self._device}")

    def _mean_pooling(self, model_output, attention_mask):
        """平均池化获取句子嵌入"""
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    def _encode_texts(self, texts: List[str]) -> List[List[float]]:
        """编码文本列表为嵌入向量"""
        all_embeddings = []

        for i in range(0, len(texts), self._batch_size):
            batch_texts = texts[i:i + self._batch_size]

            encoded_input = self._tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='pt'
            ).to(self._device)

            with torch.no_grad():
                model_output = self._model(**encoded_input)

            embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])

            if self._normalize_embeddings:
                embeddings = F.normalize(embeddings, p=2, dim=1)

            batch_embeddings = embeddings.cpu().numpy().tolist()
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _get_query_embedding(self, query: str) -> List[float]:
        """获取查询的embedding"""
        try:
            embeddings = self._encode_texts([query])
            return embeddings[0]
        except Exception as e:
            raise Exception(f"获取查询embedding失败: {str(e)}")

    def _get_text_embedding(self, text: str) -> List[float]:
        """获取单个文本的embedding"""
        try:
            embeddings = self._encode_texts([text])
            return embeddings[0]
        except Exception as e:
            raise Exception(f"获取文本embedding失败: {str(e)}")

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本embeddings"""
        try:
            return self._encode_texts(texts)
        except Exception as e:
            raise Exception(f"批量获取embeddings失败: {str(e)}")

    # 异步方法实现
    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._get_text_embeddings(texts)

    @property
    def embedding_dimension(self) -> int:
        """返回嵌入向量的维度"""
        if hasattr(self._model.config, 'hidden_size'):
            return self._model.config.hidden_size
        else:
            test_embedding = self._get_text_embedding("test")
            return len(test_embedding)