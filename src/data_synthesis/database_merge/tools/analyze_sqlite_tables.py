#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite数据库表数量分析工具
分析CSpider数据集中每个SQLite数据库包含的表数量
"""

import sqlite3
import os
from pathlib import Path
import json

def analyze_sqlite_database(db_path):
    """
    分析单个SQLite数据库的表数量

    Args:
        db_path (str): SQLite数据库文件路径

    Returns:
        dict: 包含数据库信息的字典
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]

        # 获取表详细信息
        table_info = {}
        for table_name in table_names:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_count = len(columns)

            table_info[table_name] = {
                'row_count': row_count,
                'column_count': column_count,
                'columns': [{'name': col[1], 'type': col[2]} for col in columns]
            }

        conn.close()

        return {
            'table_count': len(table_names),
            'table_names': table_names,
            'table_info': table_info,
            'status': 'success'
        }

    except Exception as e:
        return {
            'table_count': 0,
            'table_names': [],
            'table_info': {},
            'status': 'error',
            'error': str(e)
        }

def scan_sqlite_databases(base_path):
    """
    扫描指定路径下的所有SQLite数据库

    Args:
        base_path (str): 基础路径

    Returns:
        dict: 所有数据库的分析结果
    """
    base_path = Path(base_path)
    results = {}

    print("正在扫描SQLite数据库...")
    print("=" * 80)

    # 递归查找所有.sqlite文件
    sqlite_files = list(base_path.rglob("*.sqlite"))
    total_files = len(sqlite_files)

    print(f"找到 {total_files} 个SQLite数据库文件\n")

    for i, db_file in enumerate(sqlite_files, 1):
        print(f"[{i:3d}/{total_files}] 分析: {db_file.relative_to(base_path)}")

        # 获取相对路径作为键
        relative_path = str(db_file.relative_to(base_path))
        db_name = db_file.parent.name

        # 分析数据库
        analysis = analyze_sqlite_database(db_file)

        results[relative_path] = {
            'database_name': db_name,
            'full_path': str(db_file),
            'analysis': analysis
        }

        if analysis['status'] == 'success':
            print(f"       表数量: {analysis['table_count']}")
            if analysis['table_names']:
                print(f"       表名称: {', '.join(analysis['table_names'])}")
        else:
            print(f"       错误: {analysis['error']}")
        print()

    return results

def generate_summary_report(results):
    """
    生成汇总报告

    Args:
        results (dict): 数据库分析结果
    """
    print("=" * 80)
    print("汇总报告")
    print("=" * 80)

    total_databases = len(results)
    successful_databases = sum(1 for r in results.values() if r['analysis']['status'] == 'success')
    total_tables = sum(r['analysis']['table_count'] for r in results.values() if r['analysis']['status'] == 'success')

    print(f"总数据库数量: {total_databases}")
    print(f"成功分析的数据库: {successful_databases}")
    print(f"总表数量: {total_tables}")
    print(f"平均每数据库表数量: {total_tables / successful_databases:.2f}" if successful_databases > 0 else "N/A")
    print()

    # 统计表数量分布
    table_counts = {}
    for db_info in results.values():
        if db_info['analysis']['status'] == 'success':
            count = db_info['analysis']['table_count']
            table_counts[count] = table_counts.get(count, 0) + 1

    print("表数量分布:")
    for count in sorted(table_counts.keys()):
        print(f"  {count}个表: {table_counts[count]}个数据库")
    print()

    # 找出表最多和最少的数据库
    if successful_databases > 0:
        max_db = max(results.values(), key=lambda x: x['analysis']['table_count'] if x['analysis']['status'] == 'success' else -1)
        min_db = min(results.values(), key=lambda x: x['analysis']['table_count'] if x['analysis']['status'] == 'success' else float('inf'))

        print(f"表最多的数据库: {max_db['database_name']} ({max_db['analysis']['table_count']}个表)")
        print(f"表最少的数据库: {min_db['database_name']} ({min_db['analysis']['table_count']}个表)")

def save_detailed_report(results, output_file="sqlite_analysis_report.json"):
    """
    保存详细分析报告到JSON文件

    Args:
        results (dict): 数据库分析结果
        output_file (str): 输出文件名
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n详细报告已保存到: {output_file}")
    except Exception as e:
        print(f"\n保存报告时出错: {e}")

def main():
    """主函数"""
    # 设置基础路径
    base_path = os.path.join(os.getcwd(), "..", "CSpider", "database")

    if not os.path.exists(base_path):
        print(f"错误: 路径 {base_path} 不存在")
        return

    print("CSpider SQLite数据库表数量分析工具")
    print("=" * 80)

    # 扫描和分析数据库
    results = scan_sqlite_databases(base_path)

    # 生成汇总报告
    generate_summary_report(results)

    # 保存详细报告
    save_detailed_report(results)

    # 输出简化的表清单
    print("\n" + "=" * 80)
    print("各数据库表数量清单")
    print("=" * 80)
    print(f"{'数据库编号':<6} {'数据库名称':<25} {'表数量':<6} {'表名称'}")
    print("-" * 80)

    for i, (path, db_info) in enumerate(sorted(results.items()), 1):
        analysis = db_info['analysis']
        if analysis['status'] == 'success':
            table_names_str = ', '.join(analysis['table_names'][:3])  # 只显示前3个表名
            if len(analysis['table_names']) > 3:
                table_names_str += f" ... (+{len(analysis['table_names'])-3}个)"
            print(f"{i:<6} {db_info['database_name']:<25} {analysis['table_count']:<6} {table_names_str}")

if __name__ == "__main__":
    main()