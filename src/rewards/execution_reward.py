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
DEFAULT_DB_PATH = r"D:\Code\ChineseSQLSynthesis\src\data_synthesis\database_merge\report\merged_cspider.sqlite"
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


def initialize_evaluation_db(db_path: str = DEFAULT_DB_PATH):
    """
    初始化评估数据库，创建必要的表结构和示例数据

    Args:
        db_path: 数据库文件路径
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        # 插入示例数据

        cursor.execute("""
            INSERT OR IGNORE INTO orders (id, user_id, product_id, quantity, order_date) 
            VALUES 
            (1, 1, 1, 1, '2023-01-15'),
            (2, 2, 2, 3, '2023-02-20'),
            (3, 3, 4, 1, '2023-03-10'),
            (4, 1, 3, 5, '2023-04-05'),
            (5, 4, 5, 2, '2023-05-12')
        """)

        conn.commit()
        print(f"Evaluation database initialized at {db_path}")


def _parse_completion_content(completion):
    """解析模型生成的SQL内容"""
    if not completion:
        return ""
    return completion[0].get("content", "") if completion else ""


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

    # # 如果没有找到代码块，尝试将整个内容作为SQL
    # # 但先检查内容是否看起来像SQL（包含SELECT、FROM等关键词）
    # sql_keywords = ['select', 'insert', 'update', 'delete', 'from', 'where', 'join']
    # content_lower = content.lower()
    # if any(keyword in content_lower for keyword in sql_keywords):
    #     return content.strip()

    return None


def sql_execution_reward(completions: list[list[dict[str, str]]], **kwargs) -> list[float]:
    """
    SQL可执行性奖励函数：检查生成的SQL语句是否可以在数据库中成功执行

    分数设计：
    - SQL可以成功执行：1.0（有奖励）
    - SQL执行失败或无法提取有效SQL：-1.0（无奖励）

    Args:
        completions: 模型生成的SQL内容列表
        **kwargs: 可选参数，可包含timeout_seconds用于设置超时时间

    Returns:
        奖励分数列表，每个元素对应一个completion的奖励
    """
    # 从kwargs获取超时时间，默认为5秒
    timeout_seconds = kwargs.get('timeout_seconds', DEFAULT_TIMEOUT_SECONDS)

    # 提取内容
    if isinstance(completions[0], str):
        completion_contents = completions
    else:
        completion_contents = [_parse_completion_content(completion) for completion in completions]

    rewards = []

    # 使用数据库连接上下文管理器
    with get_db_connection() as conn:
        for content in completion_contents:
            # 从内容中提取SQL语句
            sql = _extract_sql_from_content(content)

            if not sql:
                rewards.append(-1.0)
                continue

            # 验证SQL执行
            result = validate_sql_execution(conn, sql, timeout_seconds)

            # 分配奖励
            if result["success"]:
                rewards.append(1.0)  # SQL执行成功，有奖励
            else:
                rewards.append(-1.0)  # SQL执行失败，无奖励

    return rewards


# 如果直接运行此文件，初始化数据库
if __name__ == "__main__":
    # initialize_evaluation_db()
    # print("SQL execution reward module is ready!")
    pass