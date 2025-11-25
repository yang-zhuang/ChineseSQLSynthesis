"""
评估指标汇总器
收集所有评估步骤的结果，计算最终评估指标
支持按照"语义等价 OR 查询匹配"规则判断最终正确性
"""

import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.evaluation.config_new.evaluation_config import (
    RESULTS_CONFIG, FINAL_EVALUATION_RULES, EVALUATION_CRITERIA
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsAggregator:
    """评估指标汇总器，用于计算最终评估指标"""

    def __init__(self):
        """初始化指标汇总器"""
        self.evaluation_rule = FINAL_EVALUATION_RULES["success_condition"]
        self.rule_description = FINAL_EVALUATION_RULES["description"]

    def load_all_results(self, model_type: str = "base_model") -> Dict[str, List[Dict]]:
        """
        加载所有评估步骤的结果

        Args:
            model_type: 模型类型 ("base_model" 或 "lora_model")

        Returns:
            包含所有步骤结果的字典
        """
        results = {}

        # 1. 加载SQL生成结果
        try:
            gen_path = RESULTS_CONFIG["sql_generation"]["base_dir"] / RESULTS_CONFIG["sql_generation"][model_type]
            results["sql_generation"] = self._load_results_file(gen_path)
            logger.info(f"Loaded {len(results['sql_generation'])} SQL generation results")
        except FileNotFoundError:
            logger.warning(f"SQL generation results not found for {model_type}")
            results["sql_generation"] = []

        # 2. 加载执行验证结果
        try:
            exec_path = RESULTS_CONFIG["execution_validation"]["base_dir"] / RESULTS_CONFIG["execution_validation"][model_type]
            results["execution_validation"] = self._load_results_file(exec_path)
            logger.info(f"Loaded {len(results['execution_validation'])} execution validation results")
        except FileNotFoundError:
            logger.warning(f"Execution validation results not found for {model_type}")
            results["execution_validation"] = []

        # 3. 加载语义等价性评估结果
        try:
            semantic_path = RESULTS_CONFIG["semantic_evaluation"]["base_dir"] / RESULTS_CONFIG["semantic_evaluation"][model_type]
            results["semantic_evaluation"] = self._load_results_file(semantic_path)
            logger.info(f"Loaded {len(results['semantic_evaluation'])} semantic evaluation results")
        except FileNotFoundError:
            logger.warning(f"Semantic evaluation results not found for {model_type}")
            results["semantic_evaluation"] = []

        return results

    def _load_results_file(self, file_path: Path) -> List[Dict]:
        """
        从JSONL文件加载结果

        Args:
            file_path: 结果文件路径

        Returns:
            结果列表
        """
        results = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        item = json.loads(line.strip())
                        if "index" not in item:
                            item["index"] = line_num - 1
                        results.append(item)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing line {line_num} in {file_path}: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error loading results from {file_path}: {e}")

        # 按index排序
        results.sort(key=lambda x: x.get("index", 0))
        return results

    def merge_results(self, all_results: Dict[str, List[Dict]], model_type) -> List[Dict]:
        """
        合并所有评估步骤的结果

        Args:
            all_results: 包含所有步骤结果的字典

        Returns:
            合并后的结果列表
        """
        # 获取最大样本数（以SQL生成结果为基准）
        max_samples = len(all_results.get("sql_generation", []))
        logger.info(f"Merging results for {max_samples} samples")

        merged_results = []

        for i in range(max_samples):
            merged_item = {
                "index": i,
                "model_type": model_type,  # 可以根据需要动态设置
            }

            # 合并SQL生成结果
            gen_results = all_results.get("sql_generation", [])
            if i < len(gen_results):
                gen_item = gen_results[i]
                merged_item.update({
                    "user_question": gen_item.get("user_question", ""),
                    "database_schema": gen_item.get("database_schema", ""),
                    "gold_sql": gen_item.get("gold_sql", ""),
                    "generated_sql": gen_item.get("generated_sql", ""),
                    "generation_success": gen_item.get("generation_success", False),
                    "raw_generation_response": gen_item.get("raw_response", ""),
                })

            # 合并执行验证结果
            exec_results = all_results.get("execution_validation", [])
            if i < len(exec_results):
                exec_item = exec_results[i]
                merged_item.update({
                    'execution_valid': exec_item.get("execution_valid", False),
                    "execution_error": exec_item.get("error_message", ""),
                })

            # 合并语义等价性评估结果
            semantic_results = all_results.get("semantic_evaluation", [])
            if i < len(semantic_results):
                semantic_item = semantic_results[i]
                merged_item.update({
                    "is_semantically_equivalent": semantic_item.get("is_semantically_equivalent", False),
                    "semantic_reason": semantic_item.get("semantic_reason", ""),
                })

            # 应用最终评估规则
            merged_item["is_overall_correct"] = self._apply_evaluation_rule(merged_item)

            merged_results.append(merged_item)

        logger.info(f"Successfully merged {len(merged_results)} samples")
        return merged_results

    def _apply_evaluation_rule(self, merged_item: Dict) -> bool:
        """
        应用最终评估规则判断样本是否正确

        规则: semantic_equivalence OR query_matching

        Args:
            merged_item: 合并后的评估结果项

        Returns:
            是否正确
        """
        # 获取各项评估结果
        semantic_equivalent = merged_item.get("is_semantically_equivalent", False)
        query_match = merged_item.get("is_query_match", False)

        # 应用规则: semantic_equivalence OR query_matching
        is_correct = semantic_equivalent or query_match

        return is_correct

    def calculate_metrics(self, merged_results: List[Dict]) -> Dict[str, Any]:
        """
        计算最终评估指标

        Args:
            merged_results: 合并后的结果列表

        Returns:
            评估指标字典
        """
        if not merged_results:
            return {"error": "No results to calculate metrics"}

        total_samples = len(merged_results)

        # 统计各项指标
        stats = {
            "total_samples": total_samples,
            "execution_validity": {
                "valid_count": 0,
                "invalid_count": 0,
                "validity_rate": 0
            },
            "semantic_equivalence": {
                "equivalent_count": 0,
                "nonequivalent_count": 0,
                "equivalence_rate": 0
            },
        }

        # 遍历所有样本进行统计
        for result in merged_results:
            # 执行有效性
            if result.get("execution_valid", False):
                stats["execution_validity"]["valid_count"] += 1
            else:
                stats["execution_validity"]["invalid_count"] += 1

            # 语义等价性
            if result.get("is_semantically_equivalent", False):
                stats["semantic_equivalence"]["equivalent_count"] += 1
            else:
                stats["semantic_equivalence"]["nonequivalent_count"] += 1

        # 计算比率
        stats["execution_validity"]["validity_rate"] = (
            stats["execution_validity"]["valid_count"] / total_samples
        )
        stats["semantic_equivalence"]["equivalence_rate"] = (
            stats["semantic_equivalence"]["equivalent_count"] / total_samples
        )

        # 添加生成时间戳
        stats["evaluation_timestamp"] = datetime.now().isoformat()

        logger.info(f"Calculated metrics for {total_samples} samples")

        return stats

    def save_metrics(self, metrics: Dict[str, Any], save_path: Path):
        """
        保存评估指标到JSON文件

        Args:
            metrics: 评估指标字典
            save_path: 保存路径
        """
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)
            logger.info(f"Metrics saved to: {save_path}")
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
            raise

    def save_detailed_results(self, merged_results: List[Dict], save_path: Path):
        """
        保存详细结果到CSV文件

        Args:
            merged_results: 合并后的结果列表
            save_path: 保存路径
        """
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # 转换为DataFrame并保存
            df = pd.DataFrame(merged_results)
            df.to_csv(save_path, index=False, encoding='utf-8-sig')
            logger.info(f"Detailed results saved to: {save_path}")
        except Exception as e:
            logger.error(f"Error saving detailed results: {e}")
            raise

    def generate_summary_report(self, metrics: Dict[str, Any]) -> str:
        """
        生成评估摘要报告

        Args:
            metrics: 评估指标字典

        Returns:
            摘要报告文本
        """
        report = []
        report.append("=" * 60)
        report.append("Text-to-SQL 评估摘要报告")
        report.append("=" * 60)
        report.append(f"评估时间: {metrics.get('evaluation_timestamp', 'Unknown')}")
        report.append(f"评估规则: {metrics.get('evaluation_rule', {}).get('description', 'Unknown')}")
        report.append(f"总样本数: {metrics['total_samples']}")
        report.append("")

        # 执行有效性
        exec_stats = metrics["execution_validity"]
        report.append("🔧 SQL执行有效性:")
        report.append(f"  - 可执行: {exec_stats['valid_count']} ({exec_stats['validity_rate']:.2%})")
        report.append(f"  - 不可执行: {exec_stats['invalid_count']} ({1-exec_stats['validity_rate']:.2%})")
        report.append("")

        # 语义等价性
        sem_stats = metrics["semantic_equivalence"]
        report.append("🎯 SQL语义等价性:")
        report.append(f"  - 等价: {sem_stats['equivalent_count']} ({sem_stats['equivalence_rate']:.2%})")
        report.append(f"  - 不等价: {sem_stats['nonequivalent_count']} ({1-sem_stats['equivalence_rate']:.2%})")
        report.append("")

        # 整体正确性
        overall_stats = metrics["overall_correctness"]
        report.append("✅ 整体正确性:")
        report.append(f"  - 正确: {overall_stats['correct_count']} ({overall_stats['correctness_rate']:.2%})")
        report.append(f"  - 错误: {overall_stats['incorrect_count']} ({1-overall_stats['correctness_rate']:.2%})")
        report.append("")

        # 关键指标总结
        report.append("🔑 关键指标:")
        report.append(f"  - 最终准确率: {overall_stats['correctness_rate']:.2%}")
        report.append(f"  - SQL可执行率: {exec_stats['validity_rate']:.2%}")
        report.append(f"  - 语义等价率: {sem_stats['equivalence_rate']:.2%}")
        report.append("=" * 60)

        return "\n".join(report)