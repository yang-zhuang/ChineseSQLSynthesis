# 表总结信息生成模块 (Generate Table Summaries)

## 模块概述

表总结信息生成模块是text-to-sql训练数据合成pipeline的第三步。该模块基于已添加注释的数据库schema，使用大语言模型为每个表生成详细的业务总结信息，包括表的用途、主要功能、业务场景等，为后续的向量相似性搜索和SQL生成提供丰富的语义上下文。

## 主要功能

### 1. 业务总结生成
- **输入**: 包含中文注释的DDL数据
- **输出**: 每个表的详细业务总结和上下文信息
- **功能**: 生成表级别的业务描述、使用场景、数据特点等

### 2. 语义信息增强
- 结合表名、字段注释、数据类型等信息
- 生成符合中文表达习惯的业务描述
- 提供多维度的表特征信息

## 执行步骤

### 步骤1: 生成DDL总结提示词
```bash
python generate_ddl_summary_prompts.py
```
- 解析带注释的DDL数据
- 为每个表生成总结请求的详细提示词
- 包含表结构、字段信息、业务背景等上下文

### 步骤2: 调用LLM生成总结
```bash
python generate_llm_responses.py.py
```
- 批量调用大语言模型API
- 生成详细的表业务总结
- 支持并发处理和断点续传

### 步骤3: 后处理LLM响应
```bash
python postprocess_llm_responses.py
```
- 清理和标准化总结文本
- 提取关键信息和标签
- 验证总结的完整性和相关性

### 步骤4: 生成最终SQL输出
```bash
python finalize_sql_outputs.py
```
- 整合总结信息和原始DDL
- 生成结构化的输出文件
- 创建处理报告和统计信息

## 核心脚本说明

### `generate_ddl_summary_prompts.py`
生成表总结请求的提示词：

**主要功能**:
- 解析带注释的DDL结构
- 分析表的字段关系和业务含义
- 生成详细的总结请求提示词

**提示词结构**:
```json
{
  "table_name": "表名",
  "table_comment": "表的中文注释",
  "columns_info": [
    {
      "column_name": "字段名",
      "column_comment": "字段注释",
      "data_type": "数据类型",
      "constraints": "约束信息"
    }
  ],
  "sample_data": "示例数据(如果有)",
  "business_context": "推断的业务背景",
  "summary_prompt": "生成的总结请求提示词"
}
```

### `generate_llm_responses.py.py`
调用LLM生成表总结：

**主要功能**:
- 并发处理大量表的总结请求
- 支持复杂提示词的批量处理
- 错误处理和响应质量监控

**LLM配置**:
- 模型: Qwen3-30B-A3B
- API端点: http://192.168.2.3:42434/v1
- 支持长文本生成和结构化输出

### `postprocess_llm_responses.py`
后处理总结内容：

**主要功能**:
- 标准化总结文本格式
- 提取关键业务特征标签
- 验证总结内容的相关性

### `finalize_sql_outputs.py`
生成最终输出：

**主要功能**:
- 整合总结和注释信息
- 生成下游处理所需的格式
- 创建详细的质量报告

## 输入输出

### 输入数据
```
# 输入：来自add_database_comments模块的JSONL文件
../add_database_comments/output/final_ddl_outputs.jsonl    # 带注释的DDL数据
```

### 输出数据
```
output/
├── table_summary_prompts.jsonl    # 表总结生成的提示词
├── llm_raw/
│   └── llm_summary_responses.jsonl     # LLM总结响应
├── postprocessed/
│   └── processed_summaries.jsonl       # 处理后的总结
└── final/
    └── final_table_outputs.jsonl       # 最终表总结输出
```

## 数据格式说明

### 实际输入数据格式
```json
{
  "table_name": "Activity",
  "create_sql": "CREATE TABLE \"Activity\" (\n                    \"actid\" INTEGER   PRIMARY KEY, \"activity_name\" varchar(25)\n                )",
  "sample_data": [
    {"actid": 770, "activity_name": "Mountain Climbing"}
  ],
  "annotated_ddl": "-- 表注释: 户外活动主表\nCREATE TABLE \"Activity\" (\n  \"actid\" INTEGER PRIMARY KEY /* 注释 */,\n  \"activity_name\" varchar(25) /* 注释 */\n);"
}
```

### 表总结提示词格式
```json
{
  "table_name": "Activity",
  "create_sql": "CREATE TABLE语句",
  "sample_data": [{"actid": 770, "activity_name": "Mountain Climbing"}],
  "annotated_ddl": "带注释的完整DDL",
  "prompt_context": {
    "prompt_template": "任务目标和要求...",
    "filled": "填充后的完整提示词..."
  }
}
```

### LLM总结输出格式
```json
{
  "summary": "活动主数据表，存储系统支持的户外运动类型基础信息（如登山、独木舟、皮划艇），用于活动报名、课程安排及用户参与记录关联。核心字段：actid（活动唯一ID，主键标识）、activity_name（活动名称，25字符内业务命名）。"
}
```

## 配置参数

### LLM配置
```python
# 总结生成专用配置
base_url = "http://192.168.2.3:42434/v1"
model_name = "Qwen3-30B-A3B"
max_tokens = 1000  # 最大生成长度
temperature = 0.7  # 生成温度
timeout = 45       # 请求超时时间
```

### 提示词配置
```python
# 总结生成的关键要素
summary_aspects = [
    "business_purpose",    # 业务目的
    "main_functions",      # 主要功能
    "data_scope",         # 数据范围
    "business_rules",     # 业务规则
    "key_relationships",  # 关键关系
    "usage_scenarios"     # 使用场景
]
```

## 提示词模板

### 表总结提示词示例
```
基于以下数据库表信息，请生成详细的业务总结：

表名: {table_name}
表注释: {table_comment}

字段信息:
{columns_info}

请从以下几个方面进行分析和总结：
1. 业务目的和主要功能
2. 涉及的业务场景和使用情况
3. 数据特点和重要字段
4. 与其他表的潜在关系
5. 业务规则和约束条件

请用中文生成自然流畅的业务总结，字数控制在200-500字之间。
```

## 质量控制

### 自动质量评估
- 总结长度合理性检查
- 关键信息完整性验证
- 业务逻辑一致性检查
- 中文表达流畅性评估

### 质量评分标准
- **完整性(40%)**: 是否覆盖主要的业务方面
- **准确性(30%)**: 信息是否与表结构匹配
- **流畅性(20%)**: 中文表达是否自然流畅
- **实用性(10%)**: 是否对下游任务有帮助

## 输出优化

### 总结结构化
- 将自然语言总结分解为结构化标签
- 提取关键业务实体和关系
- 生成标准化的业务分类

### 语义增强
- 生成同义词和相关概念
- 识别业务领域的专业术语
- 建立表之间的语义关联

## 注意事项

1. **业务理解准确性**: 总结需要准确反映表的实际业务用途
2. **信息一致性**: 确保总结与字段注释的一致性
3. **语言表达质量**: 生成符合中文习惯的流畅表达
4. **处理效率**: 大量表的处理需要合理的并发控制

## 后续步骤

生成的表总结信息将作为下一个模块`vector_table_similarity`的输入，用于进行向量化的表相似性搜索，找到语义相似的表。

## 故障排除

### 常见问题
1. **总结过于简单**: 增加提示词中的具体要求和示例
2. **业务理解偏差**: 提供更多的上下文信息和业务背景
3. **生成内容不一致**: 调整temperature参数和增加few-shot示例
4. **处理速度慢**: 优化并发配置和批处理大小

### 性能优化
- 使用批处理提高LLM调用效率
- 实现智能缓存避免重复请求
- 分阶段处理大量表数据
- 监控和调整资源使用情况