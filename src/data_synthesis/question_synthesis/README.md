# 问题生成模块 (Question Synthesis)

## 模块概述

问题生成模块是text-to-sql训练数据合成pipeline的第七步。该模块基于前面步骤生成的SQL查询，使用大语言模型为每个SQL生成对应的中文自然语言问题，形成完整的问句-SQL对，为text-to-sql模型的训练提供高质量的数据样本。

## 主要功能

### 1. 自然语言问题生成
- **输入**: SQL查询语句和相关上下文
- **输出**: 对应的中文自然语言问题
- **功能**: 生成各种风格和复杂度的问题文本

### 2. 问题多样性控制
- 支持多种问题风格(口语化、正式、命令式等)
- 涵盖不同复杂度层次的问题表述
- 确保问题与SQL的语义一致性

## 执行步骤

### 步骤1: 生成问题合成提示词
```bash
python generate_question_synthesis_prompts_zh.py
```

### 步骤2: 调用LLM生成问题
```bash
python generate_llm_responses.py.py
```

### 步骤3: 后处理LLM响应
```bash
python postprocess_llm_responses.py
```

### 步骤4: 生成最终问题输出
```bash
python finalize_sql_outputs.py
```

## 核心脚本说明

### `generate_question_synthesis_prompts_zh.py`
生成中文问题合成的提示词：

**主要功能**:
- 解析SQL查询的结构和意图
- 构造详细的问题生成请求提示词
- 包含SQL上下文、业务场景、问题风格要求

### `generate_llm_responses.py.py`
调用LLM生成自然语言问题：

**主要功能**:
- 批量处理问题生成请求
- 生成多种风格和复杂度的问题
- 确保问题与SQL的语义匹配

### `postprocess_llm_responses.py`
后处理问题生成结果：

**主要功能**:
- 清理和标准化问题文本
- 验证问题与SQL的语义一致性
- 提取问题特征和标签

### `finalize_sql_outputs.py`
生成最终问题输出：

**主要功能**:
- 整合问题和SQL信息
- 生成标准化的训练数据格式
- 创建质量评估报告

### `doris_query_synthesis_llm_generator.py`
专门的Doris查询问题生成器：

**主要功能**:
- 针对Doris数据库特性优化问题生成
- 支持OLAP场景的特定问题模式
- 提供分析型问题的专项生成

## 数据格式

### 输入数据格式
```json
{
  "sql_query": "SELECT COUNT(*) FROM users WHERE age > 18",
  "table_name": "users",
  "query_type": "aggregate_query",
  "complexity_level": 2,
  "business_intent": "统计成年用户数量",
  "tables_involved": ["users"],
  "functions_used": ["COUNT"],
  "table_context": {
    "table_comment": "用户信息表",
    "column_comments": {
      "age": "用户年龄",
      "name": "用户姓名"
    },
    "business_summary": "存储平台用户的基本信息"
  }
}
```

### 问题生成输出格式
```json
{
  "sql_query": "SELECT COUNT(*) FROM users WHERE age > 18",
  "question_variants": [
    {
      "question_text": "我想知道有多少个成年用户？",
      "question_style": "口语化",
      "complexity_level": "简单",
      "question_intent": "统计查询",
      "key_entities": ["成年用户", "数量"],
      "question_type": "how_many"
    },
    {
      "question_text": "请查询年龄大于18岁的用户总数",
      "question_style": "正式",
      "complexity_level": "简单",
      "question_intent": "统计查询",
      "key_entities": ["用户", "年龄", "总数"],
      "question_type": "count_query"
    }
  ],
  "generation_metadata": {
    "prompt_used": "使用的提示词",
    "model_response": "LLM原始响应",
    "generation_time": "生成时间",
    "confidence_score": 0.92
  },
  "quality_metrics": {
    "semantic_consistency": 0.95,
    "language_naturalness": 0.9,
    "complexity_match": 0.85,
    "business_relevance": 0.92
  }
}
```

## 问题生成策略

### 问题风格分类
1. **口语化风格**:
   - "我想知道..."
   - "帮我查一下..."
   - "有多少个..."

2. **正式风格**:
   - "请查询..."
   - "统计..."
   - "分析..."

3. **命令式风格**:
   - "列出所有..."
   - "显示..."
   - "找出..."

4. **疑问式风格**:
   - "哪些...?"
   - "多少...?"
   - "如何...?"

## 配置参数

### LLM配置
```python
# 问题生成专用配置
base_url = "http://192.168.2.3:42434/v1"
model_name = "Qwen3-30B-A3B"
max_tokens = 1000      # 问题生成长度适中
temperature = 0.6      # 较高温度增加表达多样性
timeout = 60
```

### 生成配置
```python
# 问题生成参数
QUESTIONS_PER_SQL = 3          # 每个SQL生成的问题数量
STYLE_DISTRIBUTION = {          # 风格分布
    "colloquial": 0.3,
    "formal": 0.3,
    "imperative": 0.2,
    "interrogative": 0.2
}
```

## 输入输出

### 输入数据
```
input/
├── final_sql_outputs.jsonl       # SQL生成结果
├── sql_prompts.jsonl           # SQL生成提示词
├── table_context.jsonl         # 表上下文信息
└── question_generation_config.json # 问题生成配置
```

### 输出数据
```
output/
├── question_synthesis_results.jsonl    # 问题生成结果
├── question_prompts.jsonl             # 问题生成提示词
├── llm_question_responses.jsonl       # LLM问题响应
├── processed_questions.jsonl         # 处理后的问题
├── final_question_outputs.jsonl      # 最终问题输出
├── question_quality_report.json      # 问题质量报告
└── question_statistics.json          # 问题统计分析
```

## 质量控制

### 问题质量评估
- **语义一致性(30%)**: 问题是否准确反映SQL意图
- **语言自然性(25%)**: 问题表达是否自然流畅
- **复杂度匹配(20%)**: 问题复杂度是否与SQL匹配
- **业务相关性(15%)**: 问题是否符合业务场景
- **多样性(10%)**: 问题风格和表述是否多样化

## 后续步骤

生成的问句-SQL对将作为下一个模块`sql_query_match_validation`的输入，进行最后的匹配验证和质量检查，确保训练数据的可靠性。

## 扩展功能

### 多语言支持
- 支持英文问题生成
- 实现中英文混合问题
- 提供多语言并行生成

### 自适应学习
- 基于用户反馈调整问题风格
- 学习最佳问题表达模式
- 持续优化生成质量

### 个性化生成
- 支持特定领域的问题生成
- 定制化的问题风格
- 业务场景专用的表达方式