"""
SQL执行奖励函数模块
用于DPO算法中评估生成的SQL语句是否可执行
"""

import re
import sqlite3
import contextlib
import os
import time
from typing import List, Dict, Any, Optional

# 默认数据库配置
DEFAULT_DB_PATH = "/root/Code/ChineseSQLSynthesis/src/data_synthesis/database_merge/report/merged_cspider.sqlite"
DEFAULT_TIMEOUT_SECONDS = 2.0


@contextlib.contextmanager
def get_db_connection(db_path: str = DEFAULT_DB_PATH):
    """
    数据库连接上下文管理器，确保连接正确关闭
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None  # 开启自动事务管理
        yield conn
    finally:
        if conn:
            conn.close()


def validate_sql_execution(conn: sqlite3.Connection, sql: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> \
Dict[str, Any]:
    """
    验证SQL语句是否可以在数据库中执行成功，带超时控制

    Args:
        conn: 数据库连接对象
        sql: 要验证的SQL语句
        timeout_seconds: 查询超时时间（秒）

    Returns:
        Dict包含验证结果信息
    """
    start_time = time.time()
    timeout_occurred = False

    def progress_handler():
        nonlocal timeout_occurred
        if time.time() - start_time > timeout_seconds:
            timeout_occurred = True
            return 1  # 非零值会中断查询
        return 0

    cursor = None
    try:
        # 设置进度处理程序，每1000个虚拟机指令调用一次
        conn.set_progress_handler(progress_handler, 1000)

        cursor = conn.cursor()
        # 开始事务
        cursor.execute("BEGIN")

        try:
            # 执行SQL语句
            cursor.execute(sql)

            # 显式回滚，确保不修改数据库
            conn.rollback()

            return {
                "success": True,
                "error": None,
                "timeout": False
            }

        except sqlite3.Error as e:
            # 检查是否是超时导致的错误
            if timeout_occurred:
                return {
                    "success": False,
                    "error": f"Query timed out after {timeout_seconds} seconds",
                    "timeout": True
                }

            # 执行出错，回滚事务
            try:
                cursor.execute("ROLLBACK")
            except:
                pass

            return {
                "success": False,
                "error": str(e),
                "timeout": False
            }

    except Exception as e:
        # 其他错误
        return {
            "success": False,
            "error": f"Execution error: {str(e)}",
            "timeout": False
        }
    finally:
        if cursor:
            cursor.close()
        # 移除进度处理程序
        conn.set_progress_handler(None, 0)


def _extract_sql_from_content(content):
    """从内容中提取SQL语句"""
    # 如果存在</think>标签，提取之后的内容
    if '</think>' in content:
        think_match = re.search("</think>(.*?)$", content, re.DOTALL)
        if think_match:
            content = think_match.group(1).strip()

    # 尝试提取```sql...```代码块
    sql_block_pattern = r"```sql\s*\n(.*?)\n```"
    matches = re.findall(sql_block_pattern, content, re.DOTALL | re.IGNORECASE)

    if matches:
        for match in matches:
            sql_code = match.strip()
            if sql_code:  # 返回第一个非空代码块
                return sql_code

    return None



# 如果直接运行此文件，初始化数据库
if __name__ == "__main__":
    # 使用数据库连接上下文管理器
    with get_db_connection() as conn:
        # 从内容中提取SQL语句
        sql = _extract_sql_from_content('sql ...')

        # 验证SQL执行
        result = validate_sql_execution(conn, sql, timeout_seconds=2)