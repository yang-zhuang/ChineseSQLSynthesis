# 数据库注释生成模块 (Add Database Comments)

## 模块概述

数据库注释生成模块是text-to-sql训练数据合成pipeline的第二步。该模块基于第一步合并的数据库，使用大语言模型为数据库中的表和字段生成中文注释，提升数据库的可读性和语义理解能力，为后续的SQL生成提供更好的上下文信息。

## 主要功能

### 1. 智能注释生成
- **输入**: 已合并的SQLite数据库 (`merged_cspider.sqlite`)
- **输出**: 包含中文注释的DDL语句和元数据
- **功能**: 基于表名、字段名、数据类型等信息生成语义化的中文注释

### 2. 结构化输出管理
- 生成标准格式的提示词模板
- 批量处理LLM响应
- 清理和验证注释质量
- 产生最终的结构化输出文件

## 执行步骤

### 步骤1: 生成DDL注释提示词
```bash
python generate_ddl_comment_prompts.py
```
- 从合并后的数据库提取schema信息
- 为每个表和字段生成注释请求提示词
- 保存为结构化的JSONL格式文件

### 步骤2: 调用LLM生成注释
```bash
python generate_llm_responses.py.py
```
- 批量调用大语言模型API
- 支持并发处理和错误重试
- 生成中文注释内容

### 步骤3: 后处理LLM响应
```bash
python postprocess_llm_responses.py
```
- 清理和标准化LLM输出格式
- 验证注释的准确性和完整性
- 过滤无效或低质量的注释

### 步骤4: 生成最终SQL输出
```bash
python finalize_sql_outputs.py
```
- 将注释整合为完整的DDL语句
- 生成可用于下游处理的格式化文件
- 生成详细的处理报告和统计信息

## 核心脚本说明

### `generate_ddl_comment_prompts.py`
生成DDL注释请求的提示词：

**主要功能**:
- 解析SQLite数据库schema
- 提取表结构和字段信息
- 生成针对中文注释的提示词模板

**输出格式**:
```json
{
  "table_name": "表名",
  "columns": [
    {
      "column_name": "字段名",
      "data_type": "数据类型",
      "is_primary_key": false,
      "is_foreign_key": false
    }
  ],
  "prompt": "生成的中文注释请求提示词"
}
```

### `generate_llm_responses.py.py`
调用大语言模型生成注释：

**主要功能**:
- 并发调用OpenAI兼容的LLM API
- 支持断点续传和错误处理
- 批量处理大量提示词

**LLM配置**:
- 模型: Qwen3-30B-A3B (本地部署)
- API端点: http://192.168.2.3:42434/v1
- 支持超时和重试机制

### `postprocess_llm_responses.py`
后处理LLM响应：

**主要功能**:
- 清理JSON格式的响应数据
- 验证注释格式的正确性
- 移除无效或重复的注释

### `finalize_sql_outputs.py`
生成最终输出：

**主要功能**:
- 将注释整合为完整DDL
- 生成下游处理所需的格式
- 创建详细的处理报告

## 输入输出

### 输入数据
```
# 输入：单个SQLite数据库文件
merged_cspider.sqlite    # 从database_merge模块输出的合并数据库
```

### 输出数据
```
output/
├── ddl_comment_prompts.jsonl      # DDL注释生成的提示词
├── llm_raw/
│   └── llm_responses.jsonl         # LLM原始响应
├── postprocessed/
│   └── processed_responses.jsonl  # 处理后的注释DDL
└── final/
    └── final_ddl_outputs.jsonl     # 最终格式化的带注释DDL
```

## 数据格式说明

### 实际输入数据
- **输入**: `merged_cspider.sqlite` (SQLite数据库文件)
- 包含694个合并后的表，每个表都有完整的schema和sample data

### DDL注释提示词输出格式
```json
{
  "table_name": "Activity",
  "create_sql": "CREATE TABLE \"Activity\" (\n                    \"actid\" INTEGER   PRIMARY KEY, \"activity_name\" varchar(25)\n                )",
  "sample_data": [
    {"actid": 770, "activity_name": "Mountain Climbing"},
    {"actid": 771, "activity_name": "Canoeing"},
    {"actid": 772, "activity_name": "Kayaking"}
  ],
  "row_count": 16,
  "prompt_context": {
    "template": "提示词模板文本...",
    "filled": "填充后的完整提示词..."
  }
}
```

### 最终注释DDL格式
```sql
-- 表注释: 户外活动主表（存储平台所有户外活动类型及唯一标识）
CREATE TABLE "Activity" (
  "actid" INTEGER PRIMARY KEY /* 活动唯一ID（系统分配的主键标识，用于活动关联和调度） */,
  "activity_name" varchar(25) /* 活动名称（标准化户外活动类型，如登山、划艇等） */
);
```

## 配置参数

### LLM配置
```python
# 在generate_llm_responses.py.py中
base_url = "http://192.168.2.3:42434/v1"
model_name = "Qwen3-30B-A3B"
timeout = 30  # 请求超时时间
enable_thinking = False  # 是否启用思考模式
```

### 处理配置
```python
# 并发处理配置
max_workers = 4  # 最大并发数
batch_size = 100  # 批处理大小
retry_attempts = 3  # 重试次数
```

## 注意事项

1. **LLM API稳定性**: 确保LLM服务稳定可用，建议配置合适的重试机制
2. **中文注释质量**: 生成的注释需要人工抽查，确保语义准确性
3. **处理性能**: 大量表的处理可能需要较长时间，建议分批处理
4. **内存使用**: 批量处理时注意内存消耗，适时调整批处理大小

## 质量控制

### 自动验证
- 检查注释格式是否符合标准
- 验证注释长度和合理性
- 确保注释与字段类型匹配

### 人工审核建议
- 抽查10%-20%的注释质量
- 关注业务核心表的注释准确性
- 验证外键字段的注释一致性

## 后续步骤

生成的带注释DDL将作为下一个模块`generate_table_summaries`的输入，用于生成表级别的业务总结信息。

## 故障排除

### 常见问题
1. **LLM API超时**: 调整timeout参数或减少并发数
2. **JSON解析错误**: 检查LLM响应格式，调整提示词模板
3. **内存不足**: 减少batch_size或max_workers参数
4. **注释质量差**: 优化提示词模板，增加示例

### 日志监控
- 监控处理进度和成功率
- 记录失败案例用于后续优化
- 统计注释长度和质量分布