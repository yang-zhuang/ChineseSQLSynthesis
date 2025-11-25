import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sqlite3
import contextlib
import time


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="从后处理结果中提取最终所需的结构化 DDL 数据")
    parser.add_argument(
        "--input_file",
        type=str,
        default="output/postprocessed/sql_responses.jsonl",
        help="后处理结果的输入文件路径"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="output/final/annotated_ddl.jsonl",
        help="成功SQL的输出文件路径"
    )
    parser.add_argument(
        "--failed_output_file",
        type=str,
        default="output/failed/failed_ddl.jsonl",
        help="失败SQL的输出文件路径"
    )
    parser.add_argument(
        "--db_path",
        type=str,
        default=r"../database_merge/report/merged_cspider.sqlite",
        help="SQLite数据库路径"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=1,
        help="每处理多少条记录后显示进度"
    )
    parser.add_argument(
        "--sql_timeout",
        type=float,
        default=3.0,
        help="SQL执行超时时间（秒）"
    )
    return parser.parse_args()


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """从 JSONL 文件加载记录，跳过无效行"""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


@contextlib.contextmanager
def get_db_connection(db_path: str):
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


def validate_sql_execution(conn: sqlite3.Connection, sql: str, timeout_seconds: float) -> Dict[str, Any]:
    """
    验证SQL语句是否可以在数据库中执行成功，带超时控制

    Args:
        conn: 数据库连接对象
        sql: 要验证的SQL语句
        timeout_seconds: 查询超时时间（秒）

    Returns:
        Dict包含验证结果信息
    """
    # 设置进度处理函数
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


def validate_sql_batch(conn: sqlite3.Connection, records: List[Dict[str, Any]], timeout_seconds: float) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    批量验证SQL语句，返回成功和失败的记录

    Args:
        conn: 数据库连接
        records: 要验证的记录列表
        timeout_seconds: SQL执行超时时间（秒）

    Returns:
        Tuple[成功记录列表, 失败记录列表]
    """
    success_records = []
    failed_records = []

    for i, data in enumerate(records):
        generated_sql = data.get('structured_response', '')

        if not generated_sql:
            print(f"记录 {i} 缺少 SQL 语句，跳过")
            continue

        # 创建记录的副本以避免修改原始数据
        record_copy = data.copy()

        # 执行验证，传入超时参数
        validation_result = validate_sql_execution(conn, generated_sql, timeout_seconds)

        if validation_result['success']:
            # 成功记录的处理
            record_copy['synthesis_sql'] = generated_sql

            # 删除不需要的字段 prompt_id
            for key in ['model_name', 'generated_content', 'structured_response']:
                if key in record_copy:
                    del record_copy[key]

            success_records.append(record_copy)
            print(f"记录 {i} SQL 执行成功")
        else:
            # 删除不需要的字段 prompt_id
            for key in ['model_name', 'generated_content', 'structured_response']:
                if key in record_copy:
                    del record_copy[key]

            # 失败记录的处理
            error_msg = f"{validation_result['error']}"
            print(f"记录 {i} {error_msg}")
            print(f"失败SQL: {generated_sql}")

            # 为失败记录添加错误信息
            record_copy['validation_error'] = {
                'error_message': validation_result['error'],
                'timeout': validation_result.get('timeout', False),
                'sql': generated_sql
            }
            failed_records.append(record_copy)

    return success_records, failed_records


def save_records_to_jsonl(records: List[Dict[str, Any]], file_path: Path):
    """将记录保存到JSONL文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()


def main():
    args = parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    # 设置输出路径
    success_output_path = Path(args.output_file)
    failed_output_path = Path(args.failed_output_file)

    # 创建输出目录
    success_output_path.parent.mkdir(parents=True, exist_ok=True)
    failed_output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 加载原始记录
    records = load_jsonl(input_path)
    print(f"共加载 {len(records)} 条后处理记录")

    # 2. 验证数据库文件是否存在
    if not Path(args.db_path).exists():
        raise FileNotFoundError(f"数据库文件不存在: {args.db_path}")

    print(f"使用数据库: {args.db_path}")
    print(f"SQL执行超时设置: {args.sql_timeout} 秒")

    success_records = []
    failed_records = []

    # 3. 使用单一数据库连接批量验证所有SQL
    with get_db_connection(args.db_path) as conn:
        print("开始批量验证SQL语句...")

        # 批量处理，显示进度
        total = len(records)
        for i in range(0, total, args.batch_size):
            batch = records[i:i + args.batch_size]
            print(f"处理进度: {i}-{min(i + args.batch_size, total)}/{total}")

            batch_success, batch_failed = validate_sql_batch(conn, batch, args.sql_timeout)
            success_records.extend(batch_success)
            failed_records.extend(batch_failed)

    # 保存成功记录
    save_records_to_jsonl(success_records, success_output_path)

    # 保存失败记录
    save_records_to_jsonl(failed_records, failed_output_path)

    # 输出统计信息
    print(f"\n✅ 数据生成完成！")
    print(f"  输入记录数: {len(records)}")
    print(f"  验证成功: {len(success_records)}")
    print(f"  验证失败: {len(failed_records)}")
    print(f"  成功记录已保存至: {success_output_path}")
    print(f"  失败记录已保存至: {failed_output_path}")


if __name__ == "__main__":
    main()