# SQL查询匹配验证模块 (SQL Query Match Validation)

## 模块概述

SQL查询匹配验证模块是text-to-sql训练数据合成pipeline的最后一步。该模块对前面生成的问句-SQL对进行全面的匹配验证和质量检查，确保问题和SQL查询的语义一致性，筛选出高质量的训练数据，为最终的text-to-sql模型训练提供可靠的数据集。

## 主要功能

### 1. 语义匹配验证
- **输入**: 问句-SQL对和相关上下文
- **输出**: 验证通过的问句-SQL对
- **功能**: 验证问题和SQL查询的语义一致性

### 2. 质量筛选和评估
- 多维度质量评估
- 自动化筛选机制
- 详细的验证报告

## 执行步骤

### 步骤1: 生成验证提示词
```bash
python generate_prompts_zh.py
```

### 步骤2: 调用LLM进行匹配验证
```bash
python generate_llm_responses.py.py
```

### 步骤3: 后处理验证结果
```bash
python postprocess_llm_responses.py
```

### 步骤4: 生成最终验证输出
```bash
python finalize_sql_outputs.py
```

## 验证标准

### 主要验证维度

#### 1. 语义一致性 (Semantic Consistency)
- **评分标准**: 0-1分数
- **评估内容**:
  - 问题意图是否被SQL准确反映
  - 查询结果是否符合问题要求
  - 条件和过滤是否匹配

#### 2. 完整性检查 (Completeness Check)
- **评分标准**: 通过/失败
- **评估内容**:
  - SQL是否完整回答问题
  - 是否遗漏问题的重要方面
  - 结果是否满足查询需求

#### 3. 可执行性验证 (Executability Verification)
- **评分标准**: 通过/失败
- **评估内容**:
  - SQL语法是否正确
  - 表和字段是否存在
  - 数据类型是否匹配

#### 4. 业务合理性 (Business Rationality)
- **评分标准**: 0-1分数
- **评估内容**:
  - 查询是否符合业务逻辑
  - 结果是否有实际意义
  - 查询场景是否真实

## 数据格式

### 验证输出格式
```json
{
  "question": "我想知道有多少个成年用户？",
  "sql_query": "SELECT COUNT(*) FROM users WHERE age > 18",
  "validation_result": {
    "overall_score": 0.92,
    "validation_passed": true,
    "detailed_scores": {
      "semantic_consistency": 0.95,
      "completeness": 1.0,
      "executability": 1.0,
      "business_rationality": 0.85
    },
    "validation_analysis": {
      "strengths": ["语义匹配度高", "SQL语法正确", "完整回答问题"],
      "weaknesses": ["业务场景可以更具体"],
      "suggestions": ["可以增加具体的业务背景"]
    }
  }
}
```

## 配置参数

### LLM配置
```python
# 验证专用配置
base_url = "http://192.168.2.3:42434/v1"
model_name = "Qwen3-30B-A3B"
max_tokens = 1500      # 验证分析可能较长
temperature = 0.2      # 低温度确保验证一致性
timeout = 90           # 验证分析需要充足时间
```

### 验证配置
```python
VALIDATION_THRESHOLDS = {
    "semantic_consistency": 0.8,
    "business_rationality": 0.7,
    "overall_quality": 0.8
}
```

## 输入输出

### 输入数据
```
input/
├── final_question_outputs.jsonl     # 问题生成结果
├── question_sql_pairs.jsonl         # 问句-SQL对
├── table_context.jsonl             # 表上下文信息
└── validation_config.json          # 验证配置
```

### 输出数据
```
output/
├── validation_results.jsonl           # 验证结果
├── validation_prompts.jsonl          # 验证提示词
├── llm_validation_responses.jsonl    # LLM验证响应
├── processed_validations.jsonl       # 处理后的验证
├── final_validated_pairs.jsonl       # 最终验证通过的问句-SQL对
└── validation_report.json            # 详细验证报告
```

## 最终输出

### 训练数据格式
```json
{
  "id": "unique_pair_id",
  "question": "我想知道有多少个成年用户？",
  "sql_query": "SELECT COUNT(*) FROM users WHERE age > 18",
  "metadata": {
    "table_name": "users",
    "question_style": "口语化",
    "complexity_level": "简单",
    "validation_score": 0.92
  },
  "quality_assurance": {
    "validated": true,
    "quality_level": "high"
  }
}
```

## Pipeline完成

验证通过后，整个text-to-sql训练数据合成pipeline完成，生成的问句-SQL对可以直接用于：
- text-to-sql模型训练
- 模型评估和测试
- 数据增强和扩展
- 持续优化和改进

这标志着从原始CSpider数据库到高质量训练数据的完整转换过程结束。