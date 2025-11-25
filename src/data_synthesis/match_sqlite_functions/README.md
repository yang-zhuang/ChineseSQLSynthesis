# SQLite函数匹配模块 (Match SQLite Functions)

## 模块概述

SQLite函数匹配模块是text-to-sql训练数据合成pipeline的第五步。该模块基于向量相似性搜索找到的相似表，为每个表匹配适合的SQLite函数，生成函数兼容性描述，为后续的SQL生成提供丰富的函数库和语义信息。

## 主要功能

### 1. 函数库管理
- **输入**: SQLite函数库和表相似性信息
- **输出**: 每个表匹配的适合函数列表
- **功能**: 基于表结构和业务场景匹配相关SQLite函数

### 2. 函数兼容性分析
- 分析函数与表结构的兼容性
- 生成函数使用的业务场景描述
- 提供函数组合的建议和约束

## 执行步骤

### 步骤1: 函数库准备和分组
```bash
# 从OmniSQL项目下载sqlite_funcs.json
# 使用LLM对函数进行智能分组
python 构造schema适配的函数名称.py
```

### 步骤2: 生成函数兼容性提示词
```bash
python generate_sqlite_function_compatibility_prompts.py
```

### 步骤3: 调用LLM生成函数匹配
```bash
python generate_llm_responses.py.py
```

### 步骤4: 后处理LLM响应
```bash
python postprocess_llm_responses.py
```

### 步骤5: 生成最终函数输出
```bash
python finalize_sql_outputs.py
```

### 步骤6: 验证和补充遗漏函数
```bash
python 判断遗漏了哪些函数.py
```

## 核心脚本说明

### `构造schema适配的函数名称.py`
构造适配表结构的函数名称：

**主要功能**:
- 基于OmniSQL的sqlite_funcs.json
- 使用LLM对函数进行智能分组
- 生成sqlite_functions_groups.json

**输出格式**:
```json
{
  "name": "函数分组名称",
  "description": "分组描述",
  "suitable_schemas": ["适合的表结构"],
  "unsuitable_schemas": ["不适合的表结构"],
  "key_functions": ["关键函数列表"]
}
```

### `generate_sqlite_function_compatibility_prompts.py`
生成函数兼容性分析提示词：

**主要功能**:
- 结合表信息和相似表信息
- 生成针对函数匹配的详细提示词
- 包含业务场景和函数使用建议

### `generate_llm_responses.py.py`
调用LLM生成函数匹配结果：

**主要功能**:
- 批量处理函数匹配请求
- 生成函数与表的兼容性分析
- 提供函数使用的具体建议

### `postprocess_llm_responses.py`
后处理函数匹配响应：

**主要功能**:
- 清理和标准化函数匹配结果
- 验证函数的适用性
- 提取关键匹配信息

### `finalize_sql_outputs.py`
生成最终函数输出：

**主要功能**:
- 整合函数匹配和兼容性信息
- 生成结构化的函数库文件
- 创建详细的匹配报告

### `判断遗漏了哪些函数.py`
检查和补充遗漏的函数：

**主要功能**:
- 分析完整函数库覆盖率
- 识别可能遗漏的重要函数
- 补充函数匹配结果

## 数据格式

### 输入数据格式
```json
{
  "table_name": "表名",
  "table_schema": "表结构信息",
  "similar_tables": [
    {
      "table_name": "相似表名",
      "similarity_score": 0.85
    }
  ],
  "business_summary": "业务总结",
  "key_entities": ["关键实体"]
}
```

### 函数匹配输出格式
```json
{
  "table_name": "表名",
  "matched_functions": [
    {
      "function_name": "函数名",
      "function_category": "函数分类",
      "compatibility_score": 0.9,
      "usage_description": "使用描述",
      "example_usage": "使用示例",
      "business_scenario": "业务场景"
    }
  ],
  "function_groups": [
    {
      "group_name": "函数组名",
      "functions": ["函数列表"],
      "suitability_reason": "适用原因"
    }
  ],
  "recommendation_summary": "匹配总结",
  "generation_metadata": {
    "model_used": "使用的模型",
    "generation_time": "生成时间",
    "confidence_score": 0.85
  }
}
```

## 函数库结构

### SQLite函数分类
基于OmniSQL的函数分类体系：

#### 聚合函数
- COUNT, SUM, AVG, MAX, MIN
- GROUP_CONCAT, TOTAL
- 自定义聚合函数

#### 字符串函数
- SUBSTR, LENGTH, UPPER, LOWER
- REPLACE, TRIM, LTRIM, RTRIM
- INSTR, LIKE, GLOB

#### 数值函数
- ABS, ROUND, FLOOR, CEIL
- RANDOM, PRINTF
- 类型转换函数

#### 日期时间函数
- DATE, TIME, DATETIME
- STRFTIME, JULIANDAY
- 时间计算函数

#### 条件和逻辑函数
- CASE, IFNULL, COALESCE
- NULLIF, IIF

#### JSON函数 (SQLite 3.38+)
- JSON_EXTRACT, JSON_ARRAY
- JSON_OBJECT, JSON_VALID

## 配置参数

### LLM配置
```python
# 函数匹配专用配置
base_url = "http://192.168.2.3:42434/v1"
model_name = "Qwen3-30B-A3B"
max_tokens = 1500
temperature = 0.3  # 较低温度确保准确性
timeout = 60
```

### 函数匹配配置
```python
# 匹配参数
MAX_FUNCTIONS_PER_TABLE = 15    # 每个表最大函数数
MIN_COMPATIBILITY_SCORE = 0.6   # 最低兼容性分数
MAX_SIMILAR_TABLES = 5         # 最大相似表数
FUNCTION_CATEGORIES = [         # 函数分类
    "aggregate", "string", "numeric",
    "datetime", "conditional", "json"
]
```

## 提示词模板

### 函数匹配提示词示例
```
基于以下表信息，为该表匹配适合的SQLite函数：

表名: {table_name}
表结构: {table_schema}
业务总结: {business_summary}
相似表: {similar_tables}

请从以下函数库中选择最适合的函数：
{function_library}

要求：
1. 选择与表结构和业务场景高度相关的函数
2. 为每个函数说明适用原因和使用场景
3. 提供具体的函数使用示例
4. 按函数优先级排序
5. 考虑函数组合的使用可能性

请输出结构化的JSON格式结果。
```

## 质量控制

### 函数匹配质量评估
- **相关性(40%)**: 函数与表业务的匹配程度
- **实用性(30%)**: 函数在实际查询中的使用频率
- **完整性(20%)**: 是否覆盖主要的查询需求
- **准确性(10%)**: 函数描述和示例的正确性

### 自动验证
- 检查函数语法正确性
- 验证函数与数据类型的兼容性
- 评估函数组合的合理性

### 人工审核建议
- 抽查核心业务表的函数匹配
- 验证复杂函数的使用示例
- 检查函数分类的准确性

## 输入输出

### 输入数据
```
# 输入：来自vector_table_similarity模块的相似性结果
../vector_table_similarity/output/similarity_results.jsonl  # 表相似性结果
sqlite_funcs.json                                          # SQLite函数库(OmniSQL)
sqlite_functions_groups.json                               # 函数分组
```

### 输出数据
```
output/
├── function_matching_results.jsonl    # 函数匹配结果
├── function_prompts.jsonl            # 匹配提示词
├── llm_function_responses.jsonl      # LLM函数响应
├── processed_functions.jsonl         # 处理后的函数
├── final_function_outputs.jsonl      # 最终函数输出
├── missing_functions_analysis.json   # 遗漏函数分析
└── function_matching_report.json     # 匹配质量报告
```

## 性能优化

### 批处理优化
- 批量处理相似表的函数匹配
- 缓存常用函数的组合模式
- 并行处理多个表的匹配请求

### 智能筛选
- 基于表结构预筛选候选函数
- 使用规则引擎过滤明显不适用的函数
- 动态调整函数匹配策略

## 故障排除

### 常见问题
1. **函数匹配过多**: 调整兼容性阈值和优先级
2. **函数描述不准确**: 优化提示词和few-shot示例
3. **遗漏重要函数**: 运行遗漏检测脚本
4. **性能问题**: 优化批处理和并发配置

### 质量改进
- 增加函数使用的具体业务场景
- 提供更多函数组合的示例
- 完善函数分类体系

## 后续步骤

生成的函数匹配结果将作为下一个模块`sql_synthesis`的输入，为SQL生成提供丰富的函数库和语义指导。

## 扩展功能

### 动态函数推荐
- 基于查询模式动态调整函数推荐
- 学习函数使用的最优组合
- 支持自定义函数的集成

### 函数性能优化
- 提供函数性能特征信息
- 建议高效的函数替代方案
- 优化复杂查询的函数选择