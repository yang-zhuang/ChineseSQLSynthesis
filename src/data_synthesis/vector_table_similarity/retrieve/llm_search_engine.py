# toolkit/retrieve/llm_search_engine.py
import json
import os
from typing import Any, List, Tuple, Dict, Union
from text2sql_evaluator.toolkit.llm.vllm_client import VLLMServiceLLM
from llama_index.core.llms import ChatMessage, MessageRole
from modelscope import AutoTokenizer
from dotenv import load_dotenv

load_dotenv()


class LLMSearchEngine:
    # 单例模式的核心：确保只有一个实例
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # 防止重复初始化（仅在第一次实例化时执行）
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 从环境变量读取大模型配置
        self.llm_url = os.getenv('LLM_URL')
        self.llm_model = os.getenv('LLM_MODEL')
        self.temperature = float(os.getenv('LLM_TEMPERATURE', 0.0))
        self.top_p = float(os.getenv('LLM_TOP_P', 0.9))
        self.max_concurrent = int(os.getenv('LLM_MAX_CONCURRENT', 10))
        self.timeout = float(os.getenv('LLM_TIMEOUT', 60.0))
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', 4096))
        self.enable_thinking = os.getenv('LLM_ENABLE_THINKING', 'false').lower() == 'true'

        # 初始化LLM和tokenizer（重量级操作，只执行一次）
        self.llm = VLLMServiceLLM(
            url=self.llm_url,
            model=self.llm_model,
            temperature=self.temperature,
            top_p=self.top_p,
            max_concurrent=self.max_concurrent,
            timeout=self.timeout,
            max_tokens=self.max_tokens,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(os.getenv('TOKENIZER_MODEL'))

        # 标记为已初始化
        self._initialized = True

    def calculate_prompt_length(self, prompt: str) -> Tuple[str, int]:
        """计算提示词的token长度（通用方法）"""
        messages = [{"role": "user", "content": prompt}]
        prompt_str = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=self.enable_thinking
        )
        token_length = len(self.tokenizer.encode(prompt_str))
        return prompt_str, token_length

    def calculate_item_length(
            self,
            query: str,
            item: Dict[str, Any],
            placeholder_mapping: Dict[str, str]
    ) -> Tuple[str, int]:
        """
        计算包含查询和item中指定字段的内容的token长度
        :param query: 用户查询文本
        :param item: 单条数据（字典）
        :param placeholder_mapping: 模板占位符到item字段的映射（如{"{user_query}": "query", "{table_info}": "schema"}）
        """
        # 构建item内容（根据映射提取字段）
        # 提取item中需要的字段（用于计算长度）
        item_content = {k: item[v] for k, v in placeholder_mapping.items() if v != "query"}
        # 组合query和单条item内容（模拟在批次中的占比）
        content = f"- query: {query}\n- item: {json.dumps(item_content, ensure_ascii=False)}"

        messages = [{"role": "user", "content": content}]

        prompt_str = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=self.enable_thinking
        )
        token_length = len(self.tokenizer.encode(prompt_str))
        return prompt_str, token_length

    def calculate_item_group_length(
            self,
            item_group: List[Dict[str, Any]],
            name_mapping: Dict[str, str],
            prompt_template: str
    ) -> Tuple[str, int]:
        """
        计算包含一组item的prompt的token长度
        :param item_group: 一组item（可能是单个item或一个批次的item）
        :param name_mapping: 占位符到item字段的映射（如{"{query}": "user_query"}）
        :param prompt_template: 提示词模板
        """
        # 根据name_mapping生成填充内容
        filled_prompt = self._fill_prompt_template(prompt_template, item_group, name_mapping)
        # 计算长度
        return self.calculate_prompt_length(filled_prompt)

    def create_batches_by_length(
        self,
        items: List[Dict[str, Any]],
        lengths: List[int],
        max_remaining_length: int
    ) -> List[List[Dict[str, Any]]]:
        """根据最大剩余长度对items进行分批（通用方法）"""
        batches = []
        current_batch = []
        current_total = 0

        for item, length in zip(items, lengths):
            if length > max_remaining_length:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_total = 0
                batches.append([item])
            else:
                if current_total + length > max_remaining_length:
                    batches.append(current_batch)
                    current_batch = [item]
                    current_total = length
                else:
                    current_batch.append(item)
                    current_total += length

        if current_batch:
            batches.append(current_batch)
        return batches

    def prepare_batch_messages(
            self,
            query: str,
            batches: List[List[Dict[str, Any]]],
            placeholder_mapping: Dict[str, str],
            prompt_template: str
    ) -> List[List[ChatMessage]]:
        """
        为每个批次准备LLM输入消息
        :param query: 用户查询文本
        :param batches: 分好批的item列表
        :param placeholder_mapping: 模板占位符到item字段的映射
        :param prompt_template: 提示词模板（含占位符）
        """
        batch_messages = []

        # 分离query占位符和item列表占位符
        query_placeholder = next((k for k, v in placeholder_mapping.items() if v == "query"), None)
        list_placeholders = {k: v for k, v in placeholder_mapping.items() if v != "query"}

        for batch in batches:
            # 替换模板中的占位符
            filled_prompt = prompt_template
            # 1. 替换query占位符（如 {user_query} → "查询2023年销售额"）
            if query_placeholder:
                filled_prompt = filled_prompt.replace(query_placeholder, query)

            # 2. 替换列表占位符（如 {table_list} → [{"table_info": "...", ...}, ...]）
            for list_placeholder, item_field in list_placeholders.items():
                # 收集批次中所有item的对应字段，组成列表
                batch_list = [item[item_field] for item in batch]
                # 替换模板中的列表占位符
                filled_prompt = filled_prompt.replace(
                    list_placeholder,
                    json.dumps(batch_list, ensure_ascii=False, indent=2)
                )

            batch_messages.append([ChatMessage(role=MessageRole.USER, content=filled_prompt)])
        return batch_messages

    def prepare_batches_and_messages(
            self,
            query: str,
            items: List[Dict[str, Any]],
            placeholder_mapping: Dict[str, str],
            prompt_template: str,
            max_prompt_length: int
    ) -> Tuple[List[List[Dict[str, Any]]], List[List[ChatMessage]]]:
        # 1. 计算模板本身的长度
        _, template_length = self.calculate_prompt_length(prompt_template)
        max_remaining_length = max_prompt_length - template_length
        if max_remaining_length <= 0:
            raise ValueError(f"模板长度超过最大允许长度（{template_length} > {max_prompt_length}）")

        # 2. 计算每个item的长度（结合query和占位符映射）
        item_lengths = []
        for item in items:
            _, length = self.calculate_item_length(query, item, placeholder_mapping)
            item_lengths.append(length)

        # 3. 分批
        batches = self.create_batches_by_length(items, item_lengths, max_remaining_length)

        # 4. 准备消息
        batch_messages = self.prepare_batch_messages(query, batches, placeholder_mapping, prompt_template)

        return batches, batch_messages

    def process_with_llm(  # 保留低阶函数
            self,
            batches: List[List[Dict[str, Any]]],
            batch_messages: List[List[ChatMessage]],
            response_key: str = "llm_response"
    ) -> List[str]:
        if len(batches) != len(batch_messages):
            raise ValueError("batches与batch_messages长度不匹配")

        batch_responses = self.llm.batch_chat_concurrent(batch_messages)
        response_list = []

        for batch_response in batch_responses.responses:
            response_content = batch_response.message.content
            response_list.append(response_content)

        return response_list

    def run_llm_search(  # 新增一站式高阶函数
            self,
            query: str,
            items: List[Dict[str, Any]],
            placeholder_mapping: Dict[str, str],
            prompt_template: str,
            max_prompt_length: int,
            response_key: str = "llm_response"
    ) -> List[Dict[str, Any]]:
        batches, batch_messages = self.prepare_batches_and_messages(
            query=query,
            items=items,
            placeholder_mapping=placeholder_mapping,
            prompt_template=prompt_template,
            max_prompt_length=max_prompt_length
        )
        return self.process_with_llm(
            batches=batches,
            batch_messages=batch_messages,
            response_key=response_key
        )

# 创建模块级全局实例，供其他模块直接导入使用
llm_searcher = LLMSearchEngine()

if __name__ == '__main__':
    import time
    from pprint import pprint

    # 1. 准备测试数据：一批文档片段（模拟实际场景中的候选数据）
    user_query = "查询2023年的销售额数据"
    candidate_tables = [
        {
            "table_name": "sales_2023",
            "doris_ddl_comment_create_sql": "CREATE TABLE sales_2023 (date DATE COMMENT '日期', amount DECIMAL COMMENT '销售额')",
            "score": 0.89
        },
        {
            "table_name": "users",
            "doris_ddl_comment_create_sql": "CREATE TABLE users (id INT COMMENT '用户ID', name STRING COMMENT '用户名')",
            "score": 0.32
        },
        {
            "table_name": "sales_2022",
            "doris_ddl_comment_create_sql": "CREATE TABLE sales_2022 (date DATE COMMENT '日期', amount DECIMAL COMMENT '销售额')",
            "score": 0.75
        }
    ]

    # 2. 定义prompt模板：要求LLM判断文档是否与查询相关
    table_matching_template = """
            请判断以下表是否与用户查询相关：
            - 用户查询：{user_query}
            - 候选表信息：{table_infos}

            输出格式：{"recommendation": {{"primary_tables": [], "tables_to_include": []}}}
            """

    placeholder_mapping = {
        "{user_query}": "query",  # 映射到外部传入的query
        "{table_infos}": "doris_ddl_comment_create_sql"  # 映射到item中的字段
    }

    responses = llm_searcher.run_llm_search(
            query=user_query,
            items=candidate_tables,
            placeholder_mapping=placeholder_mapping,
            prompt_template=table_matching_template,
            max_prompt_length=120+70  # 单个prompt最大长度
    )
    print("纯响应列表（长度与items一致）：")
    for i, resp in enumerate(responses):
        print(f"响应{i + 1}：{resp}...")  # 打印前50字符
    # # 4. 批量处理（分批 + 生成消息）
    # batches, batch_messages = llm_searcher.batch_search(
    #     query=user_query,
    #     items=candidate_tables,
    #     placeholder_mapping=placeholder_mapping,
    #     prompt_template=table_matching_template,
    #     max_prompt_length=120+70  # 单个prompt最大长度
    # )
    #
    # # 5. 打印结果
    # print(f"分批次结果（共{len(batches)}批）：")
    # for i, batch in enumerate(batches):
    #     print(f"\n第{i + 1}批包含{len(batch)}张表：")
    #     for table in batch:
    #         print(f"- {table['table_name']}")
    #
    # print(f"\n生成的消息数量：{len(batch_messages)}")