# 数据库合并模块 (Database Merge)

## 模块概述

数据库合并模块是text-to-sql训练数据合成pipeline的第一步。该模块负责将CSpider中文数据集中的多个SQLite数据库合并成一个统一的数据库文件(`merged_cspider.sqlite`)，为后续的数据增强和合成步骤提供基础数据源。

## 主要功能

### 1. 数据库整合
- **输入**: CSpider数据集中的多个独立SQLite数据库文件
- **输出**: 单一合并后的SQLite数据库文件
- **功能**: 解决表名冲突、主键重复、外键约束等问题

### 2. 数据验证与报告
- 生成详细的合并报告，包含统计信息
- 记录冲突解决过程和数据转换日志
- 验证合并后数据库的完整性

## 执行步骤

### 步骤1: 准备CSpider数据
确保已下载CSpider数据集并解压到指定目录：
```bash
# 推荐使用full_CSpider.zip (2024年更新版)
# 下载地址: https://drive.google.com/drive/folders/1TxCUq1ydPuBdDdHF3MkHT-8zixluQuLa
```

### 步骤2: 分析现有数据库
```bash
cd tools
python analyze_schemas.py          # 分析数据库结构
python analyze_sqlite_tables.py   # 检查表结构
python test_merge_logic.py        # 测试合并逻辑
```

### 步骤3: 执行数据库合并
```bash
cd tools
python merge_sqlite_databases.py
```

## 核心脚本说明

### `merge_sqlite_databases.py`
主要的数据库合并脚本，包含`SQLiteMerger`类：

**主要功能**:
- 表名冲突解决 (添加数据库前缀)
- 外键关系维护
- 数据完整性验证
- 详细的合并日志记录

**配置参数**:
- `output_db`: 输出数据库路径
- `log_file`: 日志文件路径
- 冲突解决策略配置

### 分析工具
- `analyze_schemas.py`: 分析所有数据库的schema结构
- `analyze_sqlite_tables.py`: 检查表的具体结构
- `test_merge_logic.py`: 测试合并逻辑的正确性

## 输入输出

### 输入数据
```
CSpider/database/
├── academic/academic.sqlite
├── activity_1/activity_1.sqlite
├── aircraft/aircraft.sqlite
├── airport/airport.sqlite
├── allergy_type/allergy_type.sqlite
└── ... (166个SQLite数据库文件)
```

### 输出数据
```
output/
├── merged_cspider.sqlite            # 合并后的统一数据库
├── sqlite_merge_log.txt             # 详细合并日志
└── reports/
    ├── merge_report_*.json          # 合并统计报告
    └── sqlite_analysis_report.json   # 数据库分析报告
```

## 配置文件

### `config/merge_config.json`
合并配置参数：
```json
{
    "output_db": "../output/merged_cspider.sqlite",
    "log_file": "../output/sqlite_merge_log.txt",
    "table_prefix_separator": "_",
    "handle_conflicts": true
}
```

## 注意事项

1. **数据备份**: 执行合并前建议备份原始数据库
2. **存储空间**: 合并后的数据库可能较大，确保有足够磁盘空间
3. **内存使用**: 大量数据合并时注意内存消耗
4. **外键约束**: 合并过程会自动处理外键关系，但需要验证结果

## 后续步骤

数据库合并完成后，生成的`merged_cspider.sqlite`将作为下一个模块`add_database_comments`的输入数据源。

## 错误处理

- **表名冲突**: 自动添加数据库名前缀解决
- **主键重复**: 重新生成主键序列
- **外键约束**: 更新外键引用关系
- **数据类型冲突**: 保持原始数据类型

## 性能优化建议

- 使用批量插入提高性能
- 适时提交事务避免内存溢出
- 并行处理多个数据库(当内存充足时)