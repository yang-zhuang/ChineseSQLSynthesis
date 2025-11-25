# SQL生成模块 (SQL Synthesis)

## 模块概述

SQL生成模块是text-to-sql训练数据合成pipeline的第六步。该模块基于前面步骤生成的完整数据上下文(带注释的DDL、表总结、相似表、函数匹配等)，使用大语言模型生成高质量的SQL查询语句，为后续的问题生成提供真实的SQL基础。

## 主要功能

### 1. SQL查询生成
- **输入**: 完整的表上下文信息和函数库
- **输出**: 高质量的SQL查询语句
- **功能**: 生成各种复杂度和类型的SQL查询

### 2. 查询多样性控制
- 支持不同复杂度的查询生成
- 涵盖多种SQL操作类型
- 确保查询的业务场景真实性

## 执行步骤

### 步骤1: 生成SQL合成提示词
```bash
python generate_sql_synthesis_prompt.py
```

### 步骤2: 调用LLM生成SQL
```bash
python generate_llm_responses.py.py
```

### 步骤3: 后处理LLM响应
```bash
python postprocess_llm_responses.py
```

### 步骤4: 生成最终SQL输出
```bash
python finalize_sql_outputs.py
```

## 核心脚本说明

### `generate_sql_synthesis_prompt.py`
生成SQL合成的提示词：

**主要功能**:
- 整合所有前期生成的上下文信息
- 构造详细的SQL生成请求提示词
- 包含表结构、注释、函数、相似表等完整信息

### `generate_llm_responses.py.py`
调用LLM生成SQL查询：

**主要功能**:
- 批量处理SQL生成请求
- 生成各种类型和复杂度的SQL
- 支持多轮对话和迭代优化

### `postprocess_llm_responses.py`
后处理SQL生成结果：

**主要功能**:
- SQL语法验证和清理
- 查询复杂度分析
- 业务场景合理性检查

### `finalize_sql_outputs.py`
生成最终SQL输出：

**主要功能**:
- 整合SQL和元数据信息
- 生成标准化的训练数据格式
- 创建质量评估报告

## SQL生成策略

### 复杂度分级
1. **简单查询(复杂度1)**:
   - 单表简单SELECT
   - 基本WHERE条件
   - 简单排序

2. **中等查询(复杂度2)**:
   - 多表连接
   - 聚合函数
   - 复杂WHERE条件

3. **复杂查询(复杂度3)**:
   - 子查询和嵌套查询
   - 窗口函数
   - 复杂聚合

4. **高度复杂查询(复杂度4)**:
   - 多层嵌套子查询
   - 复杂窗口函数
   - 多种函数组合

## 配置参数

### LLM配置
```python
# SQL生成专用配置
base_url = "http://192.168.2.3:42434/v1"
model_name = "Qwen3-30B-A3B"
max_tokens = 2000      # SQL生成可能较长
temperature = 0.4      # 中等温度，确保准确性同时有一定创造性
timeout = 90           # SQL生成可能需要更多时间
```

### 生成配置
```python
# SQL生成参数
MAX_QUERIES_PER_TABLE = 10     # 每个表最大查询数
COMPLEXITY_DISTRIBUTION = {     # 复杂度分布
    "simple": 0.4,
    "moderate": 0.3,
    "complex": 0.2,
    "highly_complex": 0.1
}
```

## 输入输出

### 输入数据
```
input/
├── final_function_outputs.jsonl    # 函数匹配结果
├── table_summaries.jsonl          # 表总结信息
├── similarity_results.jsonl       # 相似性结果
├── annotated_ddl.jsonl            # 带注释的DDL
└── sql_generation_config.json     # SQL生成配置
```

### 输出数据
```
output/
├── sql_synthesis_results.jsonl    # SQL生成结果
├── sql_prompts.jsonl             # SQL生成提示词
├── llm_sql_responses.jsonl       # LLM SQL响应
├── processed_sql.jsonl           # 处理后的SQL
├── final_sql_outputs.jsonl       # 最终SQL输出
├── sql_quality_report.json       # SQL质量报告
└── query_statistics.json         # 查询统计分析
```

## 数据格式

### SQL生成输出格式
```json
{
  "table_name": "表名",
  "sql_query": "生成的SQL语句",
  "query_type": "查询类型(SELECT, JOIN, AGGREGATE等)",
  "complexity_level": "复杂度等级(1-4)",
  "business_intent": "业务意图描述",
  "expected_result": "预期结果说明",
  "functions_used": ["使用的函数列表"],
  "tables_involved": ["涉及的表列表"],
  "query_explanation": "查询逻辑解释",
  "generation_metadata": {
    "prompt_used": "使用的提示词",
    "model_response": "LLM原始响应",
    "generation_time": "生成时间",
    "confidence_score": "置信度分数"
  },
  "quality_metrics": {
    "syntax_correctness": 1.0,
    "business_relevance": 0.9,
    "complexity_appropriateness": 0.85,
    "function_usage_quality": 0.9
  }
}
```

## 质量控制

### SQL质量评估
- **语法正确性(30%)**: SQL语法是否正确
- **业务相关性(25%)**: 是否符合业务场景
- **复杂度适当性(20%)**: 复杂度是否合适
- **函数使用质量(15%)**: 函数使用是否合理
- **查询效率(10%)**: 查询是否高效

## 后续步骤

生成的SQL查询将作为下一个模块`question_synthesis`的输入，用于生成对应的自然语言问题，形成完整的问句-SQL对。

## 故障排除

### 常见问题
1. **SQL语法错误**: 加强语法检查和提示词优化
2. **查询不实用**: 增加业务场景的具体性要求
3. **复杂度不匹配**: 调整复杂度判断逻辑
4. **函数使用不当**: 优化函数匹配和推荐

### 改进措施
- 增加SQL执行验证
- 提供更多查询示例
- 优化提示词模板
- 实现自动质量评估

## 扩展功能

### 查询执行验证
- 在实际数据库上执行生成的SQL
- 验证查询结果的正确性
- 优化查询性能

### 多样化查询生成
- 支持不同业务场景的查询
- 生成特定领域的专业查询
- 实现查询风格的多样化

### 自适应学习
- 基于质量反馈调整生成策略
- 学习最佳查询模式
- 持续优化生成质量