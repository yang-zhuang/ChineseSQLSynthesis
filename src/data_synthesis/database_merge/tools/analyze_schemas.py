#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema文件分析工具
通过分析schema.sql文件来统计每个数据库的表数量
"""

import os
import re
from pathlib import Path

def parse_schema_sql(schema_path):
    """
    解析schema.sql文件，提取表信息

    Args:
        schema_path (str): schema.sql文件路径

    Returns:
        dict: 包含表信息的字典
    """
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用正则表达式匹配CREATE TABLE语句
        # 匹配CREATE TABLE "table_name" 或 CREATE TABLE table_name
        table_pattern = r'CREATE\s+TABLE\s+(?:"([^"]+)"|(\S+))\s*\('
        matches = re.findall(table_pattern, content, re.IGNORECASE)

        # 提取表名（处理引号）
        tables = []
        for match in matches:
            table_name = match[0] if match[0] else match[1]
            tables.append(table_name)

        return {
            'table_count': len(tables),
            'table_names': tables,
            'status': 'success'
        }

    except Exception as e:
        return {
            'table_count': 0,
            'table_names': [],
            'status': 'error',
            'error': str(e)
        }

def analyze_all_schemas(base_path):
    """
    分析所有schema.sql文件

    Args:
        base_path (str): 基础路径

    Returns:
        dict: 所有schema的分析结果
    """
    base_path = Path(base_path)
    results = {}

    print("正在扫描schema.sql文件...")
    print("=" * 80)

    # 查找所有schema.sql文件
    schema_files = list(base_path.rglob("schema.sql"))
    total_files = len(schema_files)

    print(f"找到 {total_files} 个schema.sql文件\n")

    for i, schema_file in enumerate(schema_files, 1):
        print(f"[{i:3d}/{total_files}] 分析: {schema_file.relative_to(base_path)}")

        # 获取数据库名称
        db_name = schema_file.parent.name
        relative_path = str(schema_file.relative_to(base_path))

        # 解析schema
        analysis = parse_schema_sql(schema_file)

        results[relative_path] = {
            'database_name': db_name,
            'full_path': str(schema_file),
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
        results (dict): schema分析结果
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

    return {
        'total_databases': total_databases,
        'successful_databases': successful_databases,
        'total_tables': total_tables,
        'table_distribution': table_counts
    }

def create_csv_report(results, output_file="database_table_counts.csv"):
    """
    创建CSV格式的报告

    Args:
        results (dict): schema分析结果
        output_file (str): 输出文件名
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("数据库名称,表数量,表名称\n")
            for path, db_info in sorted(results.items()):
                analysis = db_info['analysis']
                if analysis['status'] == 'success':
                    table_names_str = '; '.join(analysis['table_names'])
                    f.write(f"{db_info['database_name']},{analysis['table_count']},\"{table_names_str}\"\n")
        print(f"\nCSV报告已保存到: {output_file}")
    except Exception as e:
        print(f"\n保存CSV报告时出错: {e}")

def main():
    """主函数"""
    # 设置基础路径
    base_path = os.path.join(os.getcwd(), "CSpider", "database")

    if not os.path.exists(base_path):
        print(f"错误: 路径 {base_path} 不存在")
        return

    print("CSpider 数据库表数量分析工具 (基于schema.sql文件)")
    print("=" * 80)

    # 分析所有schema文件
    results = analyze_all_schemas(base_path)

    # 生成汇总报告
    summary = generate_summary_report(results)

    # 创建CSV报告
    create_csv_report(results)

    # 输出简化的表清单
    print("\n" + "=" * 80)
    print("各数据库表数量清单")
    print("=" * 80)
    print(f"{'编号':<4} {'数据库名称':<25} {'表数量':<4} {'表名称'}")
    print("-" * 80)

    for i, (path, db_info) in enumerate(sorted(results.items()), 1):
        analysis = db_info['analysis']
        if analysis['status'] == 'success':
            table_names_str = ', '.join(analysis['table_names'][:2])  # 只显示前2个表名
            if len(analysis['table_names']) > 2:
                table_names_str += f" ... (+{len(analysis['table_names'])-2}个)"
            print(f"{i:<4} {db_info['database_name']:<25} {analysis['table_count']:<4} {table_names_str}")

if __name__ == "__main__":
    main()