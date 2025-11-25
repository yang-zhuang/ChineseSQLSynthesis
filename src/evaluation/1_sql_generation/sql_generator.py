"""
SQL生成器 - 用于生成Text-to-SQL预测结果
支持并发处理以提高效率
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import concurrent.futures
from tqdm import tqdm

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from openai import OpenAI
from src.evaluation.config_new.model_config import TEXT2SQL_MODELS
from src.evaluation.config_new.evaluation_config import PROMPT_FILES

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLGenerator:
    """SQL生成器，支持基础模型和LoRA模型的并发批量生成"""

    def __init__(self, model_type: str = "base_model", max_workers: int = 5):
        """
        初始化SQL生成器

        Args:
            model_type: 模型类型 ("base_model" 或 "lora_model")
            max_workers: 并发工作线程数
        """
        if model_type not in TEXT2SQL_MODELS:
            raise ValueError(f"Unknown model type: {model_type}")

        self.model_config = TEXT2SQL_MODELS[model_type]
        self.model_type = model_type
        self.max_workers = max_workers
        self.client = None
        self._prompt_template = self._load_prompt_template()
        # 编译正则表达式（只编译一次，提升性能）
        self._prompt_patterns = self._compile_prompt_patterns()

    def _load_prompt_template(self) -> str:
        """加载Text-to-SQL生成提示词模板"""
        try:
            prompt_path = PROMPT_FILES["text2sql"]
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

            with open(prompt_path, encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            raise

    def _compile_prompt_patterns(self) -> Dict[str, re.Pattern]:
        """编译prompt解析所需的正则表达式（缓存编译结果）"""
        return {
            "db_engine": re.compile(r"- \*\*数据库引擎\*\*：(.*?)- \*\*数据库模式（Schema）\*\*：", re.DOTALL),
            "db_schema": re.compile(r"- \*\*数据库模式（Schema）\*\*：(.*?)- \*\*（可选）示例数据\*\*：", re.DOTALL),
            "sample_data": re.compile(r"- \*\*（可选）示例数据\*\*：(.*?)## 用户问题", re.DOTALL),
            "user_question": re.compile(r"## 用户问题(.*?)## 生成规则", re.DOTALL),
        }

    def init_client(self) -> OpenAI:
        """初始化OpenAI客户端"""
        try:
            self.client = OpenAI(
                base_url=self.model_config["api_url"],
                api_key=self.model_config["api_key"]
            )
            return self.client
        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            raise ConnectionError(f"Client initialization failed: {str(e)}")

    def _extract_sql_from_response(self, response_text: str) -> Optional[str]:
        """
        从模型响应中提取SQL语句

        Args:
            response_text: 模型原始响应文本

        Returns:
            提取的SQL语句或None
        """
        try:
            # 移除思考标签
            if "</think>" in response_text:
                match = re.search(r"</think>(.*?)$", response_text, re.DOTALL)
                if match:
                    response_text = match.group(1).strip()

            # 提取SQL代码块
            sql_block_pattern = r"```sql\s*\n(.*?)\n```"
            matches = re.findall(sql_block_pattern, response_text, re.DOTALL | re.IGNORECASE)

            if matches:
                for match in matches:
                    sql_code = match.strip()
                    if sql_code:
                        return sql_code

            return None

        except Exception as e:
            logger.error(f"Error extracting SQL from response: {e}")
            return None

    def _parse_prompt_content(self, prompt: str) -> Dict[str, str]:
        """
        单独提取prompt解析逻辑：处理匹配失败场景，返回默认值
        """
        patterns = self._prompt_patterns
        return {
            "db_engine": patterns["db_engine"].search(prompt).group(1).strip() if patterns["db_engine"].search(
                prompt) else "",
            "db_schema": patterns["db_schema"].search(prompt).group(1).strip() if patterns["db_schema"].search(
                prompt) else "",
            "sample_data": patterns["sample_data"].search(prompt).group(1).strip() if patterns["sample_data"].search(
                prompt) else "",
            "user_question": patterns["user_question"].search(prompt).group(1).strip() if patterns[
                "user_question"].search(prompt) else "",
        }

    def _generate_single_sql(self, data_item: Dict, database_engine='sqlite') -> Dict:
        """
        为单个数据项生成SQL查询

        Args:
            data_item: 包含user_question和database_schema的数据项

        Returns:
            包含生成结果的字典
        """

        # 初始化默认结果（避免异常时变量未定义）
        index = data_item.get("index", -1)
        default_result = {
            "index": index,
            "user_question": "",
            "database_schema": "",
            "sample_data": "",
            "db_engine": "",
            "gold_sql": data_item.get("ground_truth", ""),
            "raw_response": "",
            "generated_sql": None,
            "generation_success": False,
            "error": "",
            "model_type": self.model_type
        }

        try:
            # 1. 校验输入数据
            if not isinstance(data_item.get("prompt"), list) or len(data_item["prompt"]) == 0:
                raise ValueError("Invalid prompt format (expected non-empty list)")
            prompt = data_item["prompt"][0].get("content", "").strip()
            if not prompt:
                raise ValueError("Empty prompt content")

            # 2. 解析prompt内容（处理匹配失败）
            parsed = self._parse_prompt_content(prompt)
            if not parsed["user_question"]:
                logger.warning(f"Item {index}: Empty user question in prompt")

            # 调用模型生成SQL
            if not self.client:
                self.init_client()

            # 3. 调用模型生成（增加超时控制）
            response = self.client.chat.completions.create(
                model=self.model_config["model_name"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.model_config["max_tokens"],
                temperature=self.model_config["temperature"],
                top_p=self.model_config["top_p"]
            )

            # 4. 处理响应
            raw_response = response.choices[0].message.content.strip()
            generated_sql = self._extract_sql_from_response(raw_response)
            generation_success = bool(generated_sql)  # 空字符串视为失败

            print("=-" * 50)
            print(raw_response)
            print()

            # 5. 构造成功结果
            result = default_result.copy()
            result.update({
                "user_question": parsed["user_question"],
                "database_schema": parsed["db_schema"],
                "sample_data": parsed["sample_data"],
                "db_engine": parsed["db_engine"],
                "gold_sql": data_item.get("ground_truth", ""),
                "raw_response": raw_response,
                "generated_sql": generated_sql or "",  # 统一返回字符串（避免None）
                "generation_success": generation_success,
                "error": ""
            })
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating SQL for item {index}: {error_msg}")
            # 构造错误结果（复用默认结果，填充错误信息）
            error_result = default_result.copy()
            error_result.update({
                "error": error_msg,
                # 保留已解析的内容（如果解析成功）
                "user_question": parsed["user_question"] if 'parsed' in locals() else "",
                "database_schema": parsed["db_schema"] if 'parsed' in locals() else "",
                "sample_data": parsed["sample_data"] if 'parsed' in locals() else "",
                "db_engine": parsed["db_engine"] if 'parsed' in locals() else "",
            })
            return error_result

    def generate_batch_sql(self, data_list: List[Dict], save_path: Path) -> Dict:
        """
        批量生成SQL查询，使用并发处理提高效率

        Args:
            data_list: 输入数据列表
            save_path: 结果保存路径

        Returns:
            生成结果统计信息
        """
        logger.info(f"Starting batch SQL generation for {len(data_list)} items using {self.model_type}")
        logger.info(f"Using {self.max_workers} concurrent workers")

        # 确保保存目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # 并发生成SQL
        results = []
        success_count = 0
        error_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(self._generate_single_sql, item): item.get("index", i)
                for i, item in enumerate(data_list)
            }

            # 收集结果（使用tqdm显示进度）
            for future in tqdm(
                concurrent.futures.as_completed(future_to_index),
                total=len(data_list),
                desc=f"Generating SQL ({self.model_type})"
            ):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result.get("generation_success", False):
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f"Error processing future for item {index}: {e}")
                    error_count += 1

        # 按index排序结果
        results.sort(key=lambda x: x.get("index", 0))

        # 保存结果
        self._save_results(results, save_path)

        # 生成统计信息
        stats = {
            "total_items": len(data_list),
            "successful_generations": success_count,
            "failed_generations": error_count,
            "success_rate": success_count / len(data_list) if data_list else 0,
            "model_type": self.model_type,
            "results_file": str(save_path)
        }

        logger.info(f"Batch generation completed. Success rate: {stats['success_rate']:.2%}")
        return stats

    def _save_results(self, results: List[Dict], save_path: Path):
        """保存生成结果到JSONL文件"""
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                for result in results:
                    f.write(json.dumps(result, ensure_ascii=False))
                    f.write("\n")
                    f.flush()
            logger.info(f"Results saved to: {save_path}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise

    @staticmethod
    def load_data(data_path: Path) -> List[Dict]:
        """
        从JSONL文件加载数据

        Args:
            data_path: 数据文件路径

        Returns:
            数据列表
        """
        try:
            data_list = []
            with open(data_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        item = json.loads(line.strip())
                        # 添加index以便后续处理
                        item["index"] = line_num - 1
                        data_list.append(item)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing line {line_num}: {e}")
                        continue

            logger.info(f"Loaded {len(data_list)} items from {data_path}")
            return data_list

        except Exception as e:
            logger.error(f"Error loading data from {data_path}: {e}")
            raise