"""
SQL语义等价性评估器
使用大模型判断生成的SQL与gold SQL是否语义等价
支持并发处理以提高效率
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
import concurrent.futures
from tqdm import tqdm

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import json_repair
from openai import OpenAI

from src.evaluation.config_new.evaluation_config import (
    PROMPT_FILES, EVALUATION_MODELS
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticEvaluator:
    """SQL语义等价性评估器，支持并发批量评估"""

    def __init__(self, max_workers: int = 5):
        """
        初始化语义评估器

        Args:
            max_workers: 并发工作线程数
        """
        self.max_workers = max_workers
        self.model_config = EVALUATION_MODELS["semantic_equivalence"]
        self.client = None
        self._prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """加载语义等价性评估提示词模板"""
        try:
            prompt_path = PROMPT_FILES["semantic_equivalence"]
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

            with open(prompt_path, encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error loading semantic evaluation prompt template: {e}")
            raise

    def init_client(self) -> OpenAI:
        """初始化OpenAI客户端"""
        try:
            self.client = OpenAI(
                base_url=self.model_config["api_url"],
                api_key=self.model_config["api_key"]
            )
            return self.client
        except Exception as e:
            logger.error(f"Failed to initialize semantic evaluation client: {e}")
            raise ConnectionError(f"Client initialization failed: {str(e)}")

    def _extract_user_question(self, text2sql_prompt: str) -> str:
        """
        从text-to-sql提示词中提取用户问题

        Args:
            text2sql_prompt: 原始text-to-sql提示词

        Returns:
            提取的用户问题
        """
        try:
            # 尝试不同的提取模式
            patterns = [
                r"## 用户问题(.*?)## 生成规则",
                r"## 用户问题(.*?)## 数据库模式",
                r"用户问题[:：](.*?)(?:\\n|\\r|$)",
                r"User Question[:：](.*?)(?:\\n|\\r|$)"
            ]

            for pattern in patterns:
                match = re.search(pattern, text2sql_prompt, re.DOTALL | re.IGNORECASE)
                if match:
                    user_question = match.group(1).strip()
                    if user_question:
                        return user_question

            logger.warning("Could not extract user question from prompt")
            return "Unknown question"

        except Exception as e:
            logger.error(f"Error extracting user question: {e}")
            return "Unknown question"

    def _parse_semantic_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析语义等价性评估响应

        Args:
            response_text: 模型响应文本

        Returns:
            解析后的评估结果
        """
        try:
            # 移除思考标签
            if "</think>" in response_text:
                match = re.search(r"</think>(.*?)$", response_text, re.DOTALL)
                if match:
                    response_text = match.group(1).strip()

            # 尝试提取JSON
            parsed_content = json_repair.loads(response_text)

            if isinstance(parsed_content, dict):
                return {
                    'is_equivalent': bool(parsed_content.get('is_equivalent', False)),
                    'reason': str(parsed_content.get('reason', 'No reason provided')),
                    'confidence': str(parsed_content.get('confidence', 'low'))
                }
            else:
                logger.warning(f"Invalid response format: {type(parsed_content)}")
                return {
                    'is_equivalent': False,
                    'reason': f'Invalid response format: {type(parsed_content)}',
                    'confidence': 'low'
                }

        except Exception as e:
            logger.error(f"Error parsing semantic evaluation response: {e}")
            return {
                'is_equivalent': False,
                'reason': f'Parsing error: {str(e)}',
                'confidence': 'low'
            }

    def _evaluate_single_semantic(self, data_item: Dict) -> Dict:
        """
        评估单个SQL的语义等价性

        Args:
            data_item: 包含SQL信息的数据项

        Returns:
            包含评估结果的字典
        """
        try:
            index = data_item.get("index", -1)
            user_question = data_item.get("user_question", "")
            gold_sql = data_item.get("gold_sql", "")
            generated_sql = data_item.get("generated_sql", "")
            model_type = data_item.get("model_type", "unknown")

            # 如果没有生成的SQL，标记为不匹配
            if not generated_sql:
                data_item['is_semantically_equivalent'] = False
                data_item['semantic_reason'] = "No SQL generated"
                data_item['semantic_confidence'] = "low"

                return data_item

            # 构建评估提示词
            prompt = (self._prompt_template.replace("{user_question}", user_question)
                                    .replace("{gold_sql}", gold_sql)
                                    .replace("{predicted_sql}", generated_sql)
             )

            # 调用评估模型
            if not self.client:
                self.init_client()

            response = self.client.chat.completions.create(
                model=self.model_config["model_name"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.1,
                top_p=0.9,
                timeout=self.model_config.get("timeout", 60)
            )

            raw_response = response.choices[0].message.content.strip()
            parsed_result = self._parse_semantic_response(raw_response)

            data_item['is_semantically_equivalent'] = parsed_result['is_equivalent']
            data_item['semantic_reason'] = parsed_result['reason']
            data_item['semantic_confidence'] = parsed_result['confidence']

            return data_item

        except Exception as e:
            logger.error(f"Error evaluating semantic equivalence for item {data_item.get('index', 'unknown')}: {e}")

            data_item['is_semantically_equivalent'] = False
            data_item['semantic_reason'] = f"Evaluation error: {str(e)}",
            data_item['semantic_confidence'] = "low"

            return data_item

    def evaluate_batch_semantic(self, data_list: List[Dict], save_path: Path) -> Dict:
        """
        批量评估SQL语义等价性，使用并发处理提高效率

        Args:
            data_list: 输入数据列表
            save_path: 结果保存路径

        Returns:
            评估结果统计信息
        """
        logger.info(f"Starting batch semantic evaluation for {len(data_list)} items")
        logger.info(f"Using {self.max_workers} concurrent workers")

        # 确保保存目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # 评估结果
        results = []
        equivalent_count = 0
        nonequivalent_count = 0
        evaluation_error_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有评估任务
            future_to_index = {
                executor.submit(self._evaluate_single_semantic, item): item.get("index", i)
                for i, item in enumerate(data_list)
            }

            # 收集结果（使用tqdm显示进度）
            for future in tqdm(
                concurrent.futures.as_completed(future_to_index),
                total=len(data_list),
                desc="Evaluating semantic equivalence"
            ):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result.get("is_semantically_equivalent", False):
                        equivalent_count += 1
                    else:
                        nonequivalent_count += 1

                except Exception as e:
                    logger.error(f"Error processing semantic evaluation future for item {index}: {e}")
                    evaluation_error_count += 1

        # 按index排序结果
        results.sort(key=lambda x: x.get("index", 0))

        # 保存结果
        self._save_results(results, save_path)

        # 计算统计信息
        stats = {
            "total_items": len(data_list),
            "semantically_equivalent": equivalent_count,
            "semantically_nonequivalent": nonequivalent_count,
            "evaluation_errors": evaluation_error_count,
            "equivalence_rate": equivalent_count / len(data_list) if data_list else 0,
            "success_rate": (equivalent_count + nonequivalent_count) / len(data_list) if data_list else 0,
            "results_file": str(save_path),
            "model_used": self.model_config["model_name"]
        }

        logger.info(f"Batch semantic evaluation completed. Equivalence rate: {stats['equivalence_rate']:.2%}")
        return stats

    def _save_results(self, results: List[Dict], save_path: Path):
        """保存评估结果到JSONL文件"""
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                for result in results:
                    f.write(json.dumps(result, ensure_ascii=False))
                    f.write('\n')
                    f.flush()
            logger.info(f"Semantic evaluation results saved to: {save_path}")
        except Exception as e:
            logger.error(f"Error saving semantic evaluation results: {e}")
            raise

    @staticmethod
    def load_execution_results(results_path: Path) -> List[Dict]:
        """
        从SQL执行验证结果文件加载数据

        Args:
            results_path: SQL执行验证结果文件路径

        Returns:
            数据列表
        """
        try:
            data_list = []
            with open(results_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        item = json.loads(line.strip())
                        # 确保有index字段
                        if "index" not in item:
                            item["index"] = line_num - 1
                        data_list.append(item)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing line {line_num}: {e}")
                        continue

            logger.info(f"Loaded {len(data_list)} execution validation results from {results_path}")
            return data_list

        except Exception as e:
            logger.error(f"Error loading execution results from {results_path}: {e}")
            raise