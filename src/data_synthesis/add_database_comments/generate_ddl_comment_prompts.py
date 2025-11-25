import sqlite3
import json
import sys
import argparse
import os
from pathlib import Path

# 默认配置常量
DEFAULT_EXCLUDED_TABLES = ["merge_metadata", "merge_conflicts"]
DEFAULT_PROMPT_TEMPLATE_PATH = "prompts/sqlite_ddl_comment_generator_prompt.txt"

DEFAULT_OUTPUT_DIR = "output/prompt"
DEFAULT_OUTPUT_FILE = os.path.join(DEFAULT_OUTPUT_DIR, "ddl_comment_prompts.jsonl")

def extract_db_info(
    db_path: str,
    sample_limit: int = 3,
    include_system_tables: bool = False,
    tables_to_skip: list[str] | None = None,
    min_sample_rows: int = 0,
) -> tuple[list[dict], list[str], list[tuple[str, int]]]:
    """
    从 SQLite 数据库中提取表结构、样本数据及行数统计。

    参数:
        db_path: SQLite 数据库文件路径
        sample_limit: 每个表最多提取的样本行数（默认: 3）
        include_system_tables: 是否包含 sqlite_ 开头的系统表（默认: False）
        tables_to_skip: 要跳过的表名列表（默认: DEFAULT_EXCLUDED_TABLES）
        min_sample_rows: 表至少需包含的行数，否则被跳过（默认: 0）

    返回:
        tuple: (
            processed_tables: list[dict] — 处理后的表信息列表,
            skipped_by_config: list[str] — 因配置跳过的表,
            skipped_for_low_row_count: list[tuple[str, int]] — 因行数不足跳过的表及其行数
        )
    """
    tables_to_skip = tables_to_skip or DEFAULT_EXCLUDED_TABLES.copy()

    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"数据库文件不存在: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 获取表名列表
    if include_system_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")

    table_names = [row[0] for row in cursor.fetchall()]

    processed_tables = []
    skipped_by_config = []
    skipped_for_low_row_count = []

    for table_name in table_names:
        if table_name in tables_to_skip:
            skipped_by_config.append(table_name)
            continue

        # 获取建表语句
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
        create_sql_row = cursor.fetchone()
        if not create_sql_row:
            continue
        create_sql = create_sql_row[0]

        # 获取行数
        row_count = None
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`;")
            row_count = cursor.fetchone()[0]
            if row_count < min_sample_rows:
                skipped_for_low_row_count.append((table_name, row_count))
                continue
        except sqlite3.Error as e:
            print(f"警告: 无法获取表 '{table_name}' 的行数: {e}", file=sys.stderr)

        # 获取列名
        cursor.execute(f"PRAGMA table_info(`{table_name}`);")
        columns = [col_info[1] for col_info in cursor.fetchall()]

        # 获取样本数据
        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT ?;", (sample_limit,))
        rows = cursor.fetchall()

        sample_data = []
        for row in rows:
            row_dict = {}
            for col_name, value in zip(columns, row):
                if isinstance(value, bytes):
                    row_dict[col_name] = f"[BINARY_DATA:{len(value)} bytes]"
                elif value is not None and not isinstance(value, (str, int, float, bool)):
                    row_dict[col_name] = str(value)
                else:
                    row_dict[col_name] = value
            sample_data.append(row_dict)

        processed_tables.append({
            "table_name": table_name,
            "create_sql": create_sql,
            "sample_data": sample_data,
            "row_count": row_count,
        })

    conn.close()
    return processed_tables, skipped_by_config, skipped_for_low_row_count


def parse_table_list(table_list_str: str) -> list[str]:
    """
    解析命令行传入的表名列表字符串，支持逗号、分号或空格分隔。
    """
    if not table_list_str.strip():
        return []
    for delimiter in [',', ';', ' ']:
        if delimiter in table_list_str:
            return [t.strip() for t in table_list_str.split(delimiter) if t.strip()]
    return [table_list_str.strip()]


def load_prompt_template(template_path: str) -> str:
    """
    从文件加载 prompt 模板。
    """
    try:
        return Path(template_path).read_text(encoding='utf-8').strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt 模板文件不存在: {template_path}")
    except Exception as e:
        raise RuntimeError(f"读取 prompt 模板失败: {e}")


def create_argument_parser() -> argparse.ArgumentParser:
    """
    创建并配置命令行参数解析器。
    """
    parser = argparse.ArgumentParser(
        description="提取 SQLite 数据库结构与样本数据，用于生成 DDL 注释 prompt"
    )
    parser.add_argument(
        "--db-path",
        default="../database_merge/report/merged_cspider.sqlite",
        help="SQLite 数据库文件路径（默认: ../数据库合并/merged_cspider.sqlite）"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="每个表最多提取的样本行数（默认: 3）"
    )
    parser.add_argument(
        "--min-rows",
        type=int,
        default=1,
        help="表至少需包含的行数才被处理（默认: 1）"
    )
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="包含 sqlite_ 开头的系统表"
    )
    parser.add_argument(
        "--skip-tables",
        type=str,
        default="",
        help='额外跳过的表名，支持逗号、分号或空格分隔，例如: "log, temp_data"'
    )
    parser.add_argument(
        "--include-merge-tables",
        action="store_true",
        help="包含默认跳过的 merge 相关表（merge_metadata, merge_conflicts）"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help=f"输出文件路径（默认: {DEFAULT_OUTPUT_FILE}）"
    )
    parser.add_argument(
        "--prompt-template",
        type=str,
        default=DEFAULT_PROMPT_TEMPLATE_PATH,
        help=f"Prompt 模板路径（默认: {DEFAULT_PROMPT_TEMPLATE_PATH}）"
    )
    return parser


def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    # 构建最终的跳过表列表
    tables_to_skip = DEFAULT_EXCLUDED_TABLES.copy()
    if args.include_merge_tables:
        for tbl in DEFAULT_EXCLUDED_TABLES:
            if tbl in tables_to_skip:
                tables_to_skip.remove(tbl)

    extra_skip_tables = parse_table_list(args.skip_tables)
    for tbl in extra_skip_tables:
        if tbl not in tables_to_skip:
            tables_to_skip.append(tbl)

    print(f"数据库路径: {args.db_path}")
    print(f"样本行数上限: {args.limit}")
    print(f"最小行数阈值: {args.min_rows}")
    print(f"跳过的表: {', '.join(tables_to_skip) if tables_to_skip else '无'}")
    print("-" * 60)

    try:
        db_info, skipped_config, skipped_low = extract_db_info(
            db_path=args.db_path,
            sample_limit=args.limit,
            include_system_tables=args.include_system,
            tables_to_skip=tables_to_skip,
            min_sample_rows=args.min_rows,
        )
    except Exception as e:
        print(f"错误: 提取数据库信息失败: {e}", file=sys.stderr)
        sys.exit(1)

    if skipped_config:
        print(f"\n因配置跳过的表: {', '.join(skipped_config)}")
    if skipped_low:
        low_info = [f"{name} ({count} 行)" for name, count in skipped_low]
        print(f"因行数不足跳过的表（需 ≥{args.min_rows} 行）: {', '.join(low_info)}")

    print(f"\n成功处理的表数量: {len(db_info)}")

    # 加载 prompt 模板（仅一次）
    try:
        prompt_template = load_prompt_template(args.prompt_template)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # ===== 确保输出目录存在 =====
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 写入输出文件（JSONL 格式）
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            for record in db_info:
                record["prompt_context"] = {
                    "template": prompt_template,
                    "filled": prompt_template.replace("{DDL_SQL}", record["create_sql"])
                                            .replace("{TABLE_DATA}", json.dumps(record["sample_data"], ensure_ascii=False, indent=2))
                }
                f.write(json.dumps(record, ensure_ascii=False))
                f.write("\n")
        print(f"\n结果已写入: {args.output}")
    except Exception as e:
        print(f"错误: 写入输出文件失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()