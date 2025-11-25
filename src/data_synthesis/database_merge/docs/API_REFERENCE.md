# 工具API和配置参考

## 分析工具 API

### analyze_sqlite_tables.py

#### 类和方法

##### `SQLiteAnalyzer`
```python
class SQLiteAnalyzer:
    def __init__(self, base_path, output_format="console"):
        """
        初始化分析器

        Args:
            base_path (str): 数据库搜索基础路径
            output_format (str): 输出格式: "console", "json", "csv"
        """
```

##### 主要方法

###### `analyze_database(db_path)`
```python
def analyze_database(self, db_path):
    """
    分析单个SQLite数据库

    Args:
        db_path (str): SQLite数据库文件路径

    Returns:
        dict: 包含表信息的字典
        {
            'table_count': int,
            'table_names': list,
            'table_info': dict,
            'status': str,
            'error': str  # 错误时存在
        }
    """
```

###### `analyze_all_databases()`
```python
def analyze_all_databases(self):
    """
    分析所有SQLite数据库

    Returns:
        dict: 所有数据库的分析结果
        {
            'database_path': {
                'database_name': str,
                'full_path': str,
                'analysis': dict
            }
        }
    """
```

###### `generate_report(results, output_file=None)`
```python
def generate_report(self, results, output_file=None):
    """
    生成分析报告

    Args:
        results (dict): 分析结果
        output_file (str, optional): 输出文件路径
    """
```

#### 使用示例

```python
from analyze_sqlite_tables import SQLiteAnalyzer

# 创建分析器
analyzer = SQLiteAnalyzer(
    base_path="./CSpider/database",
    output_format="json"
)

# 分析所有数据库
results = analyzer.analyze_all_databases()

# 生成报告
analyzer.generate_report(results, "analysis_report.json")

# 获取统计信息
summary = analyzer.get_summary()
print(f"总数据库数: {summary['total_databases']}")
print(f"总表数: {summary['total_tables']}")
```

### 分析配置选项

```json
{
  "analysis_config": {
    "input_path": "./CSpider/database",
    "file_pattern": "*.sqlite",
    "recursive_search": true,
    "output_formats": ["console", "json", "csv"],
    "include_table_details": true,
    "include_sample_data": false,
    "max_sample_rows": 5
  }
}
```

## 合并工具 API

### merge_sqlite_databases.py

#### 类和方法

##### `SQLiteMerger`
```python
class SQLiteMerger:
    def __init__(self, output_db="merged_cspider.sqlite",
                 log_file="sqlite_merge_log.txt",
                 config_file="merge_config.json"):
        """
        初始化合并器

        Args:
            output_db (str): 输出数据库文件名
            log_file (str): 日志文件名
            config_file (str): 配置文件路径
        """
```

##### 主要方法

###### `initialize_output_database()`
```python
def initialize_output_database(self):
    """
    初始化输出数据库

    Returns:
        bool: 初始化是否成功
    """
```

###### `get_database_schema(db_path)`
```python
def get_database_schema(self, db_path):
    """
    获取数据库的完整结构

    Args:
        db_path (str): SQLite数据库文件路径

    Returns:
        dict: 数据库结构信息
        {
            'tables': dict,
            'foreign_keys': dict,
            'indexes': dict
        }
    """
```

###### `resolve_table_name_conflict(original_table, db_name, existing_tables)`
```python
def resolve_table_name_conflict(self, original_table, db_name, existing_tables):
    """
    解决表名冲突

    Args:
        original_table (str): 原始表名
        db_name (str): 数据库名
        existing_tables (set): 已存在的表名集合

    Returns:
        str: 解决冲突后的新表名
    """
```

###### `copy_table_data(source_db, source_table, target_table)`
```python
def copy_table_data(self, source_db, source_table, target_table):
    """
    复制表数据，处理主键冲突

    Args:
        source_db (str): 源数据库路径
        source_table (str): 源表名
        target_table (str): 目标表名

    Returns:
        int: 成功插入的行数
    """
```

###### `merge_single_database(db_path)`
```python
def merge_single_database(self, db_path):
    """
    合并单个数据库

    Args:
        db_path (str): 数据库文件路径

    Returns:
        bool: 合并是否成功
    """
```

###### `merge_all_databases(base_path)`
```python
def merge_all_databases(self, base_path):
    """
    合并所有SQLite数据库

    Args:
        base_path (str): 基础路径
    """
```

#### 使用示例

```python
from merge_sqlite_databases import SQLiteMerger

# 创建合并器
merger = SQLiteMerger(
    output_db="custom_merged.sqlite",
    log_file="custom_merge.log"
)

# 初始化输出数据库
if not merger.initialize_output_database():
    print("初始化失败")
    exit(1)

# 合并所有数据库
try:
    merger.merge_all_databases("./CSpider/database")
    merger.generate_merge_report()
    print("合并完成！")
except Exception as e:
    print(f"合并失败: {e}")
finally:
    merger.close()
```

## 配置文件参考

### merge_config.json 完整配置

```json
{
  "database_merge_config": {
    "input_settings": {
      "base_path": "./CSpider/database",
      "database_pattern": "*.sqlite",
      "recursive_search": true,
      "exclude_patterns": ["temp_*.sqlite", "backup_*.sqlite"]
    },
    "output_settings": {
      "output_database": "merged_cspider.sqlite",
      "backup_existing": true,
      "compress_output": false,
      "output_directory": "./output"
    },
    "conflict_resolution": {
      "table_name_conflicts": {
        "strategy": "prefix_with_database_name",
        "max_table_name_length": 50,
        "separator": "_",
        "case_sensitive": false,
        "custom_resolver": null
      },
      "primary_key_conflicts": {
        "strategy": "skip_duplicate",
        "log_conflicts": true,
        "max_conflict_logs_per_table": 5,
        "conflict_threshold": 100
      },
      "data_type_conflicts": {
        "strategy": "use_source_type",
        "allow_type_conversion": true,
        "log_conversions": true,
        "strict_mode": false
      }
    },
    "validation_settings": {
      "check_foreign_keys": true,
      "verify_data_integrity": true,
      "create_statistics": true,
      "validate_schemas": true,
      "max_validation_errors": 10
    },
    "logging": {
      "log_level": "INFO",
      "log_file": "sqlite_merge_log.txt",
      "include_timestamps": true,
      "max_log_file_size": "10MB",
      "log_sql_statements": false,
      "rotate_logs": true
    },
    "performance": {
      "batch_size": 1000,
      "commit_frequency": "per_database",
      "memory_limit": "1GB",
      "temp_directory": "./temp",
      "parallel_processing": false,
      "worker_threads": 2,
      "connection_pool_size": 5
    },
    "reporting": {
      "generate_json_report": true,
      "generate_csv_summary": true,
      "include_table_statistics": true,
      "report_file_prefix": "merge_report_",
      "detailed_logging": false
    },
    "error_handling": {
      "continue_on_error": true,
      "max_retries": 3,
      "retry_delay": 1.0,
      "error_threshold": 10
    }
  }
}
```

### 配置参数说明

#### input_settings
- `base_path`: 数据库搜索基础路径
- `database_pattern`: 数据库文件匹配模式
- `recursive_search`: 是否递归搜索子目录
- `exclude_patterns`: 排除的文件模式列表

#### output_settings
- `output_database`: 输出数据库文件名
- `backup_existing`: 是否备份现有输出文件
- `compress_output`: 是否压缩输出数据库
- `output_directory`: 输出目录

#### conflict_resolution
- `table_name_conflicts`: 表名冲突解决策略
  - `strategy`: 解决策略 (`prefix_with_database_name`, `append_suffix`, `custom`)
  - `max_table_name_length`: 最大表名长度
  - `separator`: 分隔符
  - `case_sensitive`: 是否区分大小写
- `primary_key_conflicts`: 主键冲突处理策略
  - `strategy`: 处理策略 (`skip_duplicate`, `override`, `merge`)
  - `log_conflicts`: 是否记录冲突
  - `max_conflict_logs_per_table`: 每个表最大冲突日志数
  - `conflict_threshold`: 冲突阈值

#### validation_settings
- `check_foreign_keys`: 是否检查外键约束
- `verify_data_integrity`: 是否验证数据完整性
- `create_statistics`: 是否创建统计信息
- `validate_schemas`: 是否验证数据库模式
- `max_validation_errors`: 最大验证错误数

#### logging
- `log_level`: 日志级别 (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `log_file`: 日志文件名
- `include_timestamps`: 是否包含时间戳
- `max_log_file_size`: 最大日志文件大小
- `log_sql_statements`: 是否记录SQL语句
- `rotate_logs`: 是否轮转日志

#### performance
- `batch_size`: 批处理大小
- `commit_frequency`: 提交频率 (`per_table`, `per_database`, `custom`)
- `memory_limit`: 内存限制
- `temp_directory`: 临时目录
- `parallel_processing`: 是否启用并行处理
- `worker_threads`: 工作线程数
- `connection_pool_size`: 连接池大小

## 实用工具函数

### 数据库工具

```python
def get_database_size(db_path):
    """获取数据库文件大小"""
    import os
    return os.path.getsize(db_path)

def get_table_count(db_path):
    """获取数据库表数量"""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_row_count(db_path, table_name):
    """获取表行数"""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    conn.close()
    return count
```

### 配置工具

```python
def load_config(config_file="merge_config.json"):
    """加载配置文件"""
    import json
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def validate_config(config):
    """验证配置文件"""
    required_keys = ['database_merge_config']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")
    return True
```

### 日志工具

```python
class MergeLogger:
    def __init__(self, log_file="merge.log"):
        self.log_file = log_file

    def log(self, message, level="INFO"):
        """记录日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
```

## 命令行接口

### 分析工具命令行参数

```bash
python analyze_sqlite_tables.py [OPTIONS]

Options:
  --path PATH          数据库搜索路径 (默认: ./CSpider/database)
  --output FORMAT      输出格式 (console|json|csv)
  --file FILE          输出文件路径
  --recursive          递归搜索子目录
  --verbose            详细输出
  --help               显示帮助信息
```

### 合并工具命令行参数

```bash
python merge_sqlite_databases.py [OPTIONS]

Options:
  --input PATH         输入数据库路径 (默认: ./CSpider/database)
  --output FILE        输出数据库文件 (默认: merged_cspider.sqlite)
  --config FILE        配置文件路径 (默认: merge_config.json)
  --log FILE           日志文件路径 (默认: sqlite_merge_log.txt)
  --batch-size SIZE    批处理大小 (默认: 1000)
  --memory-limit SIZE  内存限制 (默认: 1GB)
  --parallel           启用并行处理
  --dry-run            模拟运行，不实际合并
  --verbose            详细输出
  --help               显示帮助信息
```

## 错误代码

### 分析工具错误代码
- `ANALYSIS_ERROR_001`: 数据库文件不存在
- `ANALYSIS_ERROR_002`: 数据库格式错误
- `ANALYSIS_ERROR_003`: 权限不足
- `ANALYSIS_ERROR_004`: 内存不足

### 合并工具错误代码
- `MERGE_ERROR_001`: 输出数据库创建失败
- `MERGE_ERROR_002`: 源数据库读取失败
- `MERGE_ERROR_003`: 表创建失败
- `MERGE_ERROR_004`: 数据插入失败
- `MERGE_ERROR_005`: 外键约束冲突
- `MERGE_ERROR_006`: 内存不足
- `MERGE_ERROR_007`: 磁盘空间不足

## 版本信息

- **当前版本**: 1.0.0
- **Python要求**: 3.6+
- **SQLite要求**: 3.15+
- **最后更新**: 2025-11-21

## 许可证

MIT License

## 支持和反馈

如有问题或建议，请：
1. 查看相关文档
2. 检查错误日志
3. 提交Issue或联系开发者