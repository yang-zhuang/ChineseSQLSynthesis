#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite数据库合并工具
将CSpider数据集中的多个SQLite数据库合并成一个统一的数据库
解决表名冲突、主键重复、外键约束等问题
"""

import sqlite3
import os
import shutil
from pathlib import Path
import hashlib
import json
from datetime import datetime
import argparse


class SQLiteMerger:
    def __init__(self, output_db, log_file, table_prefix_max_len=50, enable_foreign_keys=True):
        self.output_db = output_db
        self.log_file = log_file
        self.table_prefix_max_len = table_prefix_max_len
        self.enable_foreign_keys = enable_foreign_keys
        self.conn = None
        self.cursor = None
        self.table_mapping = {}  # 数据库名 -> 表名映射
        self.conflict_resolution = {}  # 冲突解决记录
        self.stats = {
            'total_databases': 0,
            'successful_merges': 0,
            'failed_merges': 0,
            'total_tables': 0,
            'total_rows': 0,
            'conflicts': 0
        }

    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)

        # 写入日志文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except Exception as e:
            print(f"写入日志文件失败: {e}")

    def initialize_output_database(self):
        """初始化输出数据库"""
        try:
            # 如果输出文件已存在，先删除
            if os.path.exists(self.output_db):
                os.remove(self.output_db)
                self.log(f"删除已存在的输出文件: {self.output_db}")

            # 创建新的数据库连接
            self.conn = sqlite3.connect(self.output_db)
            self.cursor = self.conn.cursor()

            # 启用外键约束
            if self.enable_foreign_keys:
                self.cursor.execute("PRAGMA foreign_keys = ON")

            # 创建元数据表来记录合并信息
            self.cursor.execute("""
                CREATE TABLE merge_metadata (
                    id INTEGER PRIMARY KEY,
                    source_database TEXT NOT NULL,
                    original_table_name TEXT NOT NULL,
                    merged_table_name TEXT NOT NULL,
                    row_count INTEGER DEFAULT 0,
                    merge_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """)

            # 创建冲突记录表
            self.cursor.execute("""
                CREATE TABLE merge_conflicts (
                    id INTEGER PRIMARY KEY,
                    conflict_type TEXT NOT NULL,
                    source_database TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    conflict_description TEXT,
                    resolution_method TEXT,
                    merge_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.conn.commit()
            self.log("输出数据库初始化成功")
            return True

        except Exception as e:
            self.log(f"初始化输出数据库失败: {e}")
            return False

    def get_database_schema(self, db_path):
        """获取数据库的完整结构"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            schema_info = {
                'tables': {},
                'foreign_keys': {},
                'indexes': {}
            }

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                schema_info['tables'][table] = columns

                # 获取外键信息
                cursor.execute(f"PRAGMA foreign_key_list({table})")
                foreign_keys = cursor.fetchall()
                if foreign_keys:
                    schema_info['foreign_keys'][table] = foreign_keys

                # 获取索引信息
                cursor.execute(f"PRAGMA index_list({table})")
                indexes = cursor.fetchall()
                if indexes:
                    schema_info['indexes'][table] = indexes

            conn.close()
            return schema_info

        except Exception as e:
            self.log(f"获取数据库结构失败 {db_path}: {e}")
            return None

    def resolve_table_name_conflict(self, original_table, db_name, existing_tables):
        """解决表名冲突"""
        # 策略：在表名前添加数据库名前缀
        base_name = f"{db_name}_{original_table}"

        # 如果名称太长，截断表名
        if len(base_name) > self.table_prefix_max_len:
            max_db_part = max(1, self.table_prefix_max_len // 2 - 5)
            max_table_part = self.table_prefix_max_len - len(db_name[:max_db_part]) - 1
            base_name = f"{db_name[:max_db_part]}_{original_table[:max_table_part]}"

        # 确保唯一性
        final_name = base_name
        counter = 1
        while final_name in existing_tables:
            final_name = f"{base_name}_{counter}"
            counter += 1

        return final_name

    def create_table_with_prefix(self, original_schema, new_table_name):
        """创建新表，保持原有结构"""
        try:
            # 重建CREATE TABLE语句
            columns = []
            primary_keys = []
            foreign_keys = []

            for col in original_schema:
                col_name = col[1]
                col_type = col[2]
                not_null = "NOT NULL" if col[3] else ""
                default_val = f"DEFAULT {col[4]}" if col[4] is not None else ""
                is_pk = "PRIMARY KEY" if col[5] else ""

                col_def = f'"{col_name}" {col_type} {not_null} {default_val} {is_pk}'
                columns.append(col_def.strip())

                if col[5]:  # 如果是主键
                    primary_keys.append(col_name)

            create_sql = f"""
                CREATE TABLE "{new_table_name}" (
                    {', '.join(columns)}
                )
            """

            self.cursor.execute(create_sql)

            # 记录冲突解决
            self.conflict_resolution[new_table_name] = {
                'original_table': original_schema[0][1] if original_schema else 'unknown',
                'resolution_method': 'prefix_with_db_name'
            }

            self.stats['conflicts'] += 1
            self.log(f"创建表: {new_table_name}")

            return True

        except Exception as e:
            self.log(f"创建表失败 {new_table_name}: {e}")
            return False

    def copy_table_data(self, source_db, source_table, target_table):
        """复制表数据，处理主键冲突"""
        try:
            source_conn = sqlite3.connect(source_db)
            source_cursor = source_conn.cursor()

            # 获取源表数据
            source_cursor.execute(f"SELECT * FROM {source_table}")
            rows = source_cursor.fetchall()

            # 获取列数
            source_cursor.execute(f"PRAGMA table_info({source_table})")
            columns = source_cursor.fetchall()
            column_count = len(columns)

            if not rows:
                source_conn.close()
                return 0

            # 准备插入语句（使用列名占位符）
            placeholders = ', '.join(['?'] * column_count)
            insert_sql = f'INSERT INTO "{target_table}" VALUES ({placeholders})'

            inserted_count = 0
            skipped_count = 0

            for row in rows:
                try:
                    self.cursor.execute(insert_sql, row)
                    inserted_count += 1
                except sqlite3.IntegrityError as e:
                    # 处理主键重复或其他完整性错误
                    skipped_count += 1
                    if skipped_count <= 5:  # 只记录前5个错误
                        self.log(f"跳过重复数据: {target_table} - {str(e)}")

            source_conn.close()

            self.log(f"数据复制完成: {source_table} -> {target_table} "
                    f"(插入: {inserted_count}, 跳过: {skipped_count})")

            return inserted_count

        except Exception as e:
            self.log(f"复制数据失败 {source_table} -> {target_table}: {e}")
            return 0

    def merge_single_database(self, db_path):
        """合并单个数据库"""
        try:
            db_name = Path(db_path).parent.name
            self.log(f"开始合并数据库: {db_name}")

            # 获取数据库结构
            schema = self.get_database_schema(db_path)
            if not schema:
                self.stats['failed_merges'] += 1
                return False

            # 获取已存在的表名
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in self.cursor.fetchall()}

            # 合并每个表
            db_table_count = 0
            db_row_count = 0

            for original_table in schema['tables']:
                # 解决表名冲突
                if original_table in existing_tables:
                    new_table_name = self.resolve_table_name_conflict(
                        original_table, db_name, existing_tables
                    )
                    self.log(f"表名冲突: {original_table} -> {new_table_name}")
                else:
                    new_table_name = original_table

                # 创建表
                table_schema = schema['tables'][original_table]
                if self.create_table_with_prefix(table_schema, new_table_name):
                    # 复制数据
                    row_count = self.copy_table_data(db_path, original_table, new_table_name)

                    # 记录元数据
                    self.cursor.execute("""
                        INSERT INTO merge_metadata
                        (source_database, original_table_name, merged_table_name, row_count)
                        VALUES (?, ?, ?, ?)
                    """, (db_name, original_table, new_table_name, row_count))

                    existing_tables.add(new_table_name)
                    db_table_count += 1
                    db_row_count += row_count

            self.stats['successful_merges'] += 1
            self.stats['total_tables'] += db_table_count
            self.stats['total_rows'] += db_row_count

            self.log(f"数据库合并完成: {db_name} "
                    f"(表: {db_table_count}, 行: {db_row_count})")

            return True

        except Exception as e:
            self.log(f"合并数据库失败 {db_path}: {e}")
            self.stats['failed_merges'] += 1
            return False

    def merge_all_databases(self, base_path):
        """合并所有SQLite数据库"""
        base_path = Path(base_path)

        # 查找所有SQLite文件
        sqlite_files = list(base_path.rglob("*.sqlite"))
        self.stats['total_databases'] = len(sqlite_files)

        self.log(f"找到 {self.stats['total_databases']} 个SQLite数据库文件")

        for db_file in sqlite_files:
            self.merge_single_database(str(db_file))

        # 提交所有更改
        if self.conn:
            self.conn.commit()

    def generate_merge_report(self):
        """生成合并报告"""
        self.log("\n" + "="*80)
        self.log("数据库合并报告")
        self.log("="*80)

        self.log(f"总数据库数量: {self.stats['total_databases']}")
        self.log(f"成功合并: {self.stats['successful_merges']}")
        self.log(f"合并失败: {self.stats['failed_merges']}")
        self.log(f"总表数量: {self.stats['total_tables']}")
        self.log(f"总数据行数: {self.stats['total_rows']}")
        self.log(f"解决的冲突: {self.stats['conflicts']}")

        # 查询合并后的表信息
        if self.conn:
            self.cursor.execute("""
                SELECT source_database, COUNT(*) as table_count,
                       SUM(row_count) as total_rows
                FROM merge_metadata
                GROUP BY source_database
                ORDER BY table_count DESC
            """)

            results = self.cursor.fetchall()
            self.log(f"\n各数据库合并统计:")
            self.log("-" * 60)
            for db_name, table_count, total_rows in results[:10]:  # 显示前10个
                self.log(f"{db_name:<25} {table_count:>3}表 {total_rows:>6}行")

        # 保存报告到文件
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'output_database': self.output_db,
            'conflict_resolution': self.conflict_resolution
        }

        report_file = f"merge_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            self.log(f"\n详细报告已保存到: {report_file}")
        except Exception as e:
            self.log(f"保存报告失败: {e}")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.log("数据库连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="合并多个 SQLite 数据库为一个统一数据库")
    parser.add_argument(
        '--input-path',
        type=str,
        default=r"D:\Code\ChineseSQLSynthesis\src\data_synthesis\database_merge\full_CSpider\CSpider\database",
        help='包含多个 SQLite 数据库的根目录（将递归搜索 *.sqlite 文件）'
    )
    parser.add_argument(
        '--output-db',
        type=str,
        default='../report/merged_cspider.sqlite',
        help='输出的合并后数据库文件路径（默认: merged_cspider.sqlite）'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        default='../report/sqlite_merge_log.txt',
        help='日志文件路径（默认: sqlite_merge_log.txt）'
    )
    parser.add_argument(
        '--table-prefix-max-len',
        type=int,
        default=50,
        help='表名前缀最大长度，用于解决冲突（默认: 50）'
    )
    parser.add_argument(
        '--disable-foreign-keys',
        action='store_true',
        help='禁用外键约束（默认启用）'
    )

    args = parser.parse_args()

    # 初始化合并器
    merger = SQLiteMerger(
        output_db=args.output_db,
        log_file=args.log_file,
        table_prefix_max_len=args.table_prefix_max_len,
        enable_foreign_keys=not args.disable_foreign_keys
    )

    Path(args.output_db).parent.mkdir(exist_ok=True)

    input_path = Path(args.input_path)
    if not input_path.exists():
        print(f"错误: 输入路径不存在: {input_path}")
        return

    try:
        print("CSpider SQLite数据库合并工具")
        print("="*80)

        # 初始化输出数据库
        if not merger.initialize_output_database():
            print("初始化失败，程序退出")
            return

        # 执行合并
        merger.merge_all_databases(args.input_path)

        # 生成报告
        merger.generate_merge_report()

        print(f"\n合并完成！输出文件: {merger.output_db}")

    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"程序执行出错: {e}")
    finally:
        merger.close()

if __name__ == "__main__":
    main()