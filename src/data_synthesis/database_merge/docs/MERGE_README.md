# CSpider SQLite数据库合并工具使用说明

## 概述

这个工具用于将CSpider数据集中的多个SQLite数据库合并成一个统一的数据库文件，解决表名冲突、主键重复、外键约束等问题。

## 合并策略和解决方法

### 主要问题识别

通过分析CSpider数据集，我们发现以下合并挑战：

1. **表名冲突**：不同数据库可能包含同名的表（如`author`, `name`, `country`等）
2. **主键重复**：多个数据库的主键值可能重叠
3. **外键约束**：跨数据库的外键关系需要重新处理
4. **数据类型不匹配**：相同字段在不同数据库中可能有不同类型
5. **数据库结构差异**：表结构可能略有不同

### 解决策略

#### 1. 表名冲突处理
- **策略**：为冲突的表名添加数据库名前缀
- **格式**：`{database_name}_{original_table_name}`
- **示例**：`car_1_author`, `academic_author`
- **长度限制**：最大50个字符（SQLite限制）

#### 2. 主键冲突处理
- **策略**：保留原始主键，跳过重复数据
- **处理方式**：捕获`IntegrityError`异常，记录冲突但不中断合并
- **日志记录**：每个表最多记录5个冲突示例

#### 3. 外键约束处理
- **策略**：重命名表时保持外键关系
- **处理方式**：更新外键引用以匹配新的表名
- **完整性**：启用外键约束检查

#### 4. 数据完整性保证
- **事务处理**：每个数据库的合并在独立事务中完成
- **错误处理**：单个表失败不影响整个数据库合并
- **回滚机制**：遇到严重错误时回滚当前事务

## 文件结构

```
merge_sqlite_databases.py    # 主合并脚本
merge_config.json            # 配置文件
MERGE_README.md              # 使用说明（本文件）
sqlite_merge_log.txt         # 运行日志（运行后生成）
merged_cspider.sqlite        # 合并后的数据库（运行后生成）
merge_report_*.json          # 合并报告（运行后生成）
```

## 使用方法

### 基本使用

```bash
python merge_sqlite_databases.py
```

### 高级使用

1. **修改配置**：编辑 `merge_config.json` 文件
2. **自定义设置**：修改脚本中的初始化参数

```python
merger = SQLiteMerger(
    output_db="custom_output.sqlite",  # 自定义输出文件名
    log_file="custom_log.txt"          # 自定义日志文件
)
```

## 配置说明

### 主要配置项

- **`input_settings`**：输入数据库设置
  - `base_path`：数据库搜索路径
  - `database_pattern`：数据库文件模式
  - `recursive_search`：是否递归搜索

- **`conflict_resolution`**：冲突解决策略
  - `table_name_conflicts`：表名冲突处理
  - `primary_key_conflicts`：主键冲突处理
  - `data_type_conflicts`：数据类型冲突处理

- **`validation_settings`**：验证设置
  - `check_foreign_keys`：检查外键约束
  - `verify_data_integrity`：验证数据完整性
  - `create_statistics`：创建统计信息

## 输出文件说明

### 1. 合并后的数据库 (`merged_cspider.sqlite`)

包含所有数据库的表和数据：
- 原始表结构保持不变
- 冲突的表被重命名
- 数据完整性得到保证

### 2. 元数据表

合并后的数据库包含两个特殊的元数据表：

#### `merge_metadata` 表
记录每个表的合并信息：
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
```

#### `merge_conflicts` 表
记录合并过程中遇到的冲突：
```sql
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

### 3. 日志文件 (`sqlite_merge_log.txt`)

详细的合并过程日志：
- 时间戳
- 操作记录
- 错误信息
- 统计数据

### 4. 合并报告 (`merge_report_*.json`)

JSON格式的详细报告：
- 合并统计信息
- 冲突解决记录
- 性能指标

## 性能考虑

### 优化策略

1. **批处理**：大表数据分批插入
2. **内存管理**：控制内存使用量
3. **事务管理**：合理设置提交频率
4. **临时文件**：使用临时目录存储中间结果

### 资源需求

- **内存**：建议至少2GB可用内存
- **磁盘空间**：需要足够空间存储合并后的数据库
- **时间**：根据数据库数量和大小，可能需要几分钟到几小时

## 注意事项

### 使用前准备

1. **备份数据**：确保原始数据库有备份
2. **检查路径**：确认数据库路径正确
3. **权限检查**：确保有读写权限

### 常见问题

1. **表名过长**：自动截断并添加序号
2. **内存不足**：调整批处理大小
3. **磁盘空间不足**：清理临时文件或更换存储位置

### 故障排除

1. **查看日志**：检查 `sqlite_merge_log.txt` 了解详细错误信息
2. **检查权限**：确保有足够的文件系统权限
3. **验证数据**：使用SQLite工具验证合并后的数据

## 示例查询

### 查看合并统计

```sql
-- 查看各数据库合并的表数量
SELECT source_database, COUNT(*) as table_count
FROM merge_metadata
GROUP BY source_database
ORDER BY table_count DESC;

-- 查看总数据行数
SELECT SUM(row_count) as total_rows
FROM merge_metadata;

-- 查看合并冲突
SELECT * FROM merge_conflicts
WHERE conflict_type = 'table_name_conflict';
```

### 验证数据完整性

```sql
-- 检查表是否存在
SELECT name FROM sqlite_master WHERE type='table';

-- 检查数据行数
SELECT COUNT(*) FROM table_name;

-- 检查外键约束
PRAGMA foreign_key_check();
```

## 扩展功能

### 自定义冲突解决策略

可以通过修改 `SQLiteMerger` 类的方法来实现自定义的冲突解决策略：

```python
def custom_table_name_conflict_resolution(self, original_table, db_name, existing_tables):
    # 实现自定义的表名冲突解决逻辑
    pass
```

### 数据过滤和转换

可以在数据复制过程中添加过滤和转换逻辑：

```python
def copy_table_data_with_transformation(self, source_db, source_table, target_table):
    # 实现数据转换逻辑
    pass
```

## 支持和反馈

如果遇到问题或需要帮助，请：

1. 查看日志文件了解详细错误信息
2. 检查合并报告中的统计数据
3. 验证输入数据库的完整性
4. 调整配置参数重试

## 版本历史

- v1.0：初始版本，支持基本的数据库合并功能
- 支持表名冲突解决、主键冲突处理、外键约束保持
- 提供详细的日志和报告功能