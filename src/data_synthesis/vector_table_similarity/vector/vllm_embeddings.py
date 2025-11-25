from typing import List, Any
from llama_index.core.embeddings import BaseEmbedding
from openai import OpenAI


class VLLMServiceEmbeddings(BaseEmbedding):
    """基于 vLLM 服务的嵌入模型"""

    def __init__(
            self,
            api_base: str = "http://localhost:8000/v1",
            api_key: str = "token-abc123",
            model_name: str = "Qwen/Qwen3-Embedding-0.6B",
            instruction: str = "Represent the Computer Science documentation or question:",
            batch_size: int = 32,
            **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self._client = OpenAI(
            base_url=api_base,
            api_key=api_key
        )

        self._model_name = model_name
        self._instruction = instruction
        self._batch_size = batch_size

    def _get_query_embedding(self, query: str) -> List[float]:
        """获取查询的embedding"""
        try:
            response = self._client.embeddings.create(
                model=self._model_name,
                input=query,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            raise Exception(f"获取查询embedding失败: {str(e)}")

    def _get_text_embedding(self, text: str) -> List[float]:
        """获取单个文本的embedding"""
        try:
            response = self._client.embeddings.create(
                model=self._model_name,
                input=text,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            raise Exception(f"获取文本embedding失败: {str(e)}")

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本embeddings"""
        try:
            all_embeddings = []

            for i in range(0, len(texts), self._batch_size):
                batch_texts = texts[i:i + self._batch_size]

                response = self._client.embeddings.create(
                    model=self._model_name,
                    input=batch_texts,
                    encoding_format="float"
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            return all_embeddings
        except Exception as e:
            raise Exception(f"批量获取embeddings失败: {str(e)}")

    # 异步方法实现
    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._get_text_embeddings(texts)