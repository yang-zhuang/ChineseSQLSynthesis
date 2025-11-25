"""
SQL执行验证器
用于验证生成的SQL是否能在数据库中成功执行
支持并发处理以提高效率
"""

import json
import logging
import time
import sqlite3
import contextlib
from pathlib import Path
from typing import Dict, List, Any, Optional
import concurrent.futures
from tqdm import tqdm

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.evaluation.config_new.evaluation_config import DEFAULT_DB_PATH, DB_TIMEOUT_SECONDS
from src.evaluation.sql_execution import _extract_sql_from_content, validate_sql_execution

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLExecutionValidator:
    """SQL执行验证器，支持并发批量验证"""

    def __init__(self, db_path: Path = None, max_workers: int = 10):
        """
        初始化SQL执行验证器

        Args:
            db_path: 数据库文件路径
            max_workers: 并发工作线程数
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.max_workers = max_workers

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        logger.info(f"Initialized validator with database: {self.db_path}")

    @contextlib.contextmanager
    def get_db_connection(self):
        """数据库连接上下文管理器，确保连接正确关闭"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.isolation_level = None  # 开启自动事务管理
            yield conn
        finally:
            if conn:
                conn.close()

    def _validate_single_sql(self, data_item: Dict) -> Dict:
        """
        验证单个SQL语句的执行

        Args:
            data_item: 包含SQL语句的数据项

        Returns:
            包含验证结果的字典
        """
        try:
            raw_response = data_item.get('raw_response', "")

            # 如果没有生成的SQL，标记为失败
            if not raw_response:
                data_item['execution_valid'] = False
                data_item['error_message'] = "No SQL generated"

                return data_item

            # 验证SQL执行
            with self.get_db_connection() as conn:
                # 提取SQL语句（如果需要）
                sql_statement = _extract_sql_from_content(raw_response) or raw_response

                # 验证SQL执行
                result = validate_sql_execution(
                    conn,
                    sql_statement,
                    timeout_seconds=DB_TIMEOUT_SECONDS
                )

            data_item['execution_valid'] = result.get('success', False)
            data_item['error_message'] = result.get('error') if not result.get('success') else None

            return data_item

        except Exception as e:
            logger.error(f"Error validating SQL for item {data_item.get('index', 'unknown')}: {e}")

            data_item['execution_valid'] = False
            data_item['error_message'] = f"Validation error: {str(e)}"

            return data_item

    def validate_batch_sql(self, data_list: List[Dict], save_path: Path) -> Dict:
        """
        批量验证SQL执行，使用并发处理提高效率

        Args:
            data_list: 输入数据列表
            save_path: 结果保存路径

        Returns:
            验证结果统计信息
        """
        logger.info(f"Starting batch SQL validation for {len(data_list)} items")
        logger.info(f"Using {self.max_workers} concurrent workers")

        # 确保保存目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # 验证结果
        results = []
        valid_count = 0
        invalid_count = 0
        timeout_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有验证任务
            future_to_index = {
                executor.submit(self._validate_single_sql, item): item.get("index", i)
                for i, item in enumerate(data_list)
            }

            # 收集结果（使用tqdm显示进度）
            for future in tqdm(
                concurrent.futures.as_completed(future_to_index),
                total=len(data_list),
                desc="Validating SQL execution"
            ):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result.get("execution_valid", False):
                        valid_count += 1
                    else:
                        invalid_count += 1
                        if result.get("timeout_occurred", False):
                            timeout_count += 1

                except Exception as e:
                    logger.error(f"Error processing validation future for item {index}: {e}")
                    invalid_count += 1

        # 按index排序结果
        results.sort(key=lambda x: x.get("index", 0))

        # 保存结果
        self._save_results(results, save_path)

        # 计算统计信息
        total_time = sum(r.get("execution_time", 0) for r in results)
        avg_time = total_time / len(results) if results else 0

        stats = {
            "total_items": len(data_list),
            "valid_executions": valid_count,
            "invalid_executions": invalid_count,
            "timeout_occurrences": timeout_count,
            "execution_rate": valid_count / len(data_list) if data_list else 0,
            "average_execution_time": avg_time,
            "total_execution_time": total_time,
            "results_file": str(save_path),
            "database_path": str(self.db_path)
        }

        logger.info(f"Batch validation completed. Execution rate: {stats['execution_rate']:.2%}")
        logger.info(f"Average execution time: {avg_time:.3f}s")

        return stats

    def _save_results(self, results: List[Dict], save_path: Path):
        """保存验证结果到JSONL文件"""
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                for result in results:
                    f.write(json.dumps(result, ensure_ascii=False))
                    f.write("\n")
                    f.flush()
            logger.info(f"Validation results saved to: {save_path}")
        except Exception as e:
            logger.error(f"Error saving validation results: {e}")
            raise

    @staticmethod
    def load_generation_results(results_path: Path) -> List[Dict]:
        """
        从SQL生成结果文件加载数据

        Args:
            results_path: SQL生成结果文件路径

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

            logger.info(f"Loaded {len(data_list)} SQL generation results from {results_path}")
            return data_list

        except Exception as e:
            logger.error(f"Error loading generation results from {results_path}: {e}")
            raise