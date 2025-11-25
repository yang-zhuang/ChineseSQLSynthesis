# 数据库合并工具完整指南

## 概述

数据库合并工具 (`merge_sqlite_databases.py`) 用于将CSpider数据集中的206个分散SQLite数据库合并为一个统一的数据库文件，智能处理各种冲突和完整性问题。

## 快速开始

### 基本使用
```bash
# 运行合并工具
python merge_sqlite_databases.py

# 查看输出文件
ls merged_cspider.sqlite sqlite_merge_log.txt
```

### 查看合并结果
```bash
# 查看合并日志
cat sqlite_merge_log.txt

# 查看统计报告
cat merge_report_*.json

# 使用SQLite客户端验证
sqlite3 merged_cspider.sqlite
```

## 核心功能

### 1. 表名冲突解决

#### 问题描述
多个数据库可能包含同名的表，如：
- `author` (学术数据库)
- `author` (汽车数据库)
- `country` (地理数据库)
- `name` (通用表名)

#### 解决策略
- **前缀策略**: 为冲突表添加数据库名前缀
- **格式**: `{database_name}_{original_table_name}`
- **示例**:
  ```
  academic_author      # 学术数据库的author表
  car_1_author         # 汽车数据库的author表
  car_1_continents     # 汽车数据库的continents表
  inn_1_rooms          # 旅馆数据库的rooms表
  ```

#### 长度处理
- SQLite表名长度限制：约50个字符
- 自动截断长表名并添加序号确保唯一性
- 示例：`very_long_database_name_some_table_1`

### 2. 主键冲突处理

#### 问题描述
多个数据库的主键值可能重叠：
```sql
-- 数据库A的author表
INSERT INTO author (aid, name) VALUES (1, "张三");

-- 数据库B的author表
INSERT INTO author (aid, name) VALUES (1, "李四");  -- 主键冲突！
```

#### 解决策略
- **保留策略**: 保持原始主键值不变
- **跳过策略**: 检测到重复主键时跳过插入
- **记录策略**: 详细记录所有冲突情况

#### 日志示例
```
[2025-11-21 10:30:15] 跳过重复数据: academic_author - UNIQUE constraint failed: author.aid
[2025-11-21 10:30:16] 跳过重复数据: car_1_author - UNIQUE constraint failed: author.aid
```

### 3. 外键约束处理

#### 问题描述
表重命名后外键引用需要更新：
```sql
-- 原始外键
FOREIGN KEY (author_id) REFERENCES author(aid)

-- 重命名后的外键
FOREIGN KEY (author_id) REFERENCES academic_author(aid)
```

#### 解决策略
- **映射更新**: 自动更新外键引用到新表名
- **约束保持**: 保持外键约束的完整性
- **验证检查**: 合并后验证外键关系的正确性

## 配置选项

### 修改默认配置
编辑 `merge_config.json` 文件来自定义合并行为：

```json
{
  "database_merge_config": {
    "output_settings": {
      "output_database": "custom_merged.sqlite",  // 自定义输出文件名
      "backup_existing": true,                    // 备份现有文件
      "compress_output": false                    // 输出压缩
    },
    "conflict_resolution": {
      "table_name_conflicts": {
        "strategy": "prefix_with_database_name",  // 冲突解决策略
        "max_table_name_length": 50,              // 最大表名长度
        "separator": "_"                          // 分隔符
      },
      "primary_key_conflicts": {
        "strategy": "skip_duplicate",             // 主键冲突策略
        "log_conflicts": true,                    // 记录冲突
        "max_conflict_logs_per_table": 5          // 每个表最大冲突日志数
      }
    },
    "performance": {
      "batch_size": 1000,                         // 批处理大小
      "commit_frequency": "per_database",         // 提交频率
      "memory_limit": "1GB",                      // 内存限制
      "temp_directory": "./temp"                  // 临时目录
    }
  }
}
```

### 高级配置选项

#### 冲突解决策略
- `"prefix_with_database_name"`: 添加数据库名前缀（默认）
- `"append_suffix"`: 添加数字后缀
- `"custom_function"`: 使用自定义函数

#### 性能优化
- **批处理大小**: 控制每次插入的记录数
- **内存限制**: 防止内存溢出
- **临时目录**: 指定临时文件位置

## 输出文件说明

### 1. 合并数据库 (merged_cspider.sqlite)

#### 结构
```sql
-- 原始数据表（重命名冲突表）
academic_author
academic_paper
car_1_author
car_1_car_makers
flight_2_airline
...
-- 其他合并的表

-- 元数据表
merge_metadata     -- 合并信息记录
merge_conflicts    -- 冲突解决记录
```

#### 元数据表结构
```sql
CREATE TABLE merge_metadata (
    id INTEGER PRIMARY KEY,
    source_database TEXT NOT NULL,
    original_table_name TEXT NOT NULL,
    merged_table_name TEXT NOT NULL,
    row_count INTEGER DEFAULT 0,
    merge_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE merge_conflicts (
    id INTEGER PRIMARY KEY,
    conflict_type TEXT NOT NULL,
    source_database TEXT NOT NULL,
    table_name TEXT NOT NULL,
    conflict_description TEXT,
    resolution_method TEXT,
    merge_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2. 合并日志 (sqlite_merge_log.txt)

#### 日志格式
```
[2025-11-21 10:30:00] CSpider SQLite数据库合并工具
[2025-11-21 10:30:00] ================================================
[2025-11-21 10:30:01] 找到 206 个SQLite数据库文件
[2025-11-21 10:30:02] [  1/206] 分析: database/academic/academic.sqlite
[2025-11-21 10:30:03]        开始合并数据库: academic
[2025-11-21 10:30:04]        创建表: author
[2025-11-21 10:30:05]        创建表: conference
[2025-11-21 10:30:06]        数据复制完成: academic (11表, 1,234行)
[2025-11-21 10:30:10] [  2/206] 分析: database/car_1/car_1.sqlite
[2025-11-21 10:30:11]        开始合并数据库: car_1
[2025-11-21 10:30:12]        表名冲突: author -> car_1_author
[2025-11-21 10:30:13]        创建表: car_1_author
[2025-11-21 10:30:14]        跳过重复数据: car_1_author - UNIQUE constraint failed: author.aid
[2025-11-21 10:30:15]        数据复制完成: car_1 (8表, 5,678行)
```

### 3. 统计报告 (merge_report_*.json)

#### 报告结构
```json
{
  "timestamp": "2025-11-21T10:30:00",
  "stats": {
    "total_databases": 206,
    "successful_merges": 204,
    "failed_merges": 2,
    "total_tables": 1,847,
    "total_rows": 2,345,678,
    "conflicts": 156
  },
  "output_database": "merged_cspider.sqlite",
  "conflict_resolution": {
    "academic_author": {
      "original_table": "author",
      "resolution_method": "prefix_with_db_name"
    }
  }
}
```

## 验证合并结果

### 1. 基本验证
```sql
-- 查看总表数
SELECT COUNT(*) FROM sqlite_master WHERE type='table';

-- 查看合并元数据
SELECT source_database, COUNT(*) as table_count, SUM(row_count) as total_rows
FROM merge_metadata
GROUP BY source_database;

-- 查看冲突记录
SELECT * FROM merge_conflicts WHERE conflict_type = 'table_name_conflict';
```

### 2. 数据完整性检查
```sql
-- 检查外键约束
PRAGMA foreign_key_check();

-- 检查表结构
.schema table_name

-- 验证数据行数
SELECT COUNT(*) FROM table_name;
```

### 3. 性能测试
```sql
-- 测试查询性能
EXPLAIN QUERY PLAN SELECT * FROM academic_author WHERE name LIKE '%张%';

-- 查看数据库统计信息
PRAGMA stats;
```

## 故障排除

### 常见问题

#### 1. 内存不足
**症状**: 合并过程中出现内存错误
**解决方案**:
```json
{
  "performance": {
    "batch_size": 500,        // 减小批处理大小
    "memory_limit": "512MB"   // 降低内存限制
  }
}
```

#### 2. 磁盘空间不足
**症状**: 写入文件时磁盘空间错误
**解决方案**:
- 清理临时文件
- 更换输出目录到有足够空间的磁盘
- 启用输出压缩

#### 3. 表名过长
**症状**: 表名截断警告
**解决方案**:
```json
{
  "conflict_resolution": {
    "table_name_conflicts": {
      "max_table_name_length": 40,    // 调整最大长度
      "separator": "__"               // 使用更短的分隔符
    }
  }
}
```

#### 4. 数据编码问题
**症状**: 中文字符显示异常
**解决方案**:
- 确保使用UTF-8编码
- 检查SQLite客户端的字符集设置
- 验证原始数据库的编码

### 调试模式

启用详细日志：
```json
{
  "logging": {
    "log_level": "DEBUG",
    "include_timestamps": true,
    "log_sql_statements": true
  }
}
```

## 性能优化

### 1. 硬件优化
- **SSD硬盘**: 显著提高I/O性能
- **内存**: 16GB+内存可减少磁盘交换
- **多核CPU**: 提高并发处理能力

### 2. 软件配置
```json
{
  "performance": {
    "batch_size": 2000,              // 增大批处理
    "commit_frequency": "per_1000_rows", // 更频繁提交
    "memory_limit": "2GB",           // 增大内存限制
    "parallel_processing": true,     // 启用并行处理
    "worker_threads": 4              // 设置工作线程数
  }
}
```

### 3. 数据库优化
```sql
-- 在合并后创建索引
CREATE INDEX idx_academic_author_name ON academic_author(name);

-- 分析数据库统计信息
ANALYZE;

-- 清理数据库
VACUUM;
```

## 扩展功能

### 1. 自定义冲突解决
```python
def custom_table_name_resolver(original_table, db_name, existing_tables):
    # 自定义表名冲突解决逻辑
    if original_table == 'author':
        return f"{db_name}_writer"
    else:
        return f"{db_name}_{original_table}"
```

### 2. 数据过滤和转换
```python
def filter_and_transform_data(row, source_table, target_table):
    # 自定义数据过滤和转换逻辑
    if 'email' in row:
        row['email'] = row['email'].lower()
    return row
```

### 3. 增量合并
```python
# 支持增量合并功能
merger = SQLiteMerger(incremental=True)
merger.merge_only_new_databases()
```

## 最佳实践

### 1. 合并前准备
- 备份原始数据
- 检查磁盘空间
- 验证数据库完整性
- 测试合并配置

### 2. 监控合并过程
- 实时查看日志文件
- 监控内存和磁盘使用
- 记录异常情况

### 3. 合并后验证
- 检查数据完整性
- 验证外键约束
- 测试常用查询
- 性能基准测试

### 4. 维护计划
- 定期重新合并
- 清理临时文件
- 更新统计信息
- 备份合并结果

## 参考资料

- [SQLite官方文档](https://sqlite.org/docs.html)
- [Python sqlite3模块文档](https://docs.python.org/3/library/sqlite3.html)
- [数据库性能优化指南](https://www.sqlite.org/optoverview.html)