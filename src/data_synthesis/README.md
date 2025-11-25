# Text-to-SQL 中文训练数据合成Pipeline

## 项目概述

本项目是一个企业级text-to-sql训练数据合成pipeline，专门针对私有数据库环境生成高质量的中文问句-SQL对训练数据。与OmniSQL ([论文链接](https://arxiv.org/pdf/2503.02240v2)) 的Web表格驱动方法不同，本方案基于真实的私有数据库，通过8.5个递进步骤和多层质量控制机制，生成更适合企业实际应用的训练数据。

**核心特色**:
- **企业级数据源**: 基于私有数据库，保护数据隐私
- **Schema导向函数匹配**: 智能匹配适用函数，非随机选择
- **倒序生成策略**: SQL → Question，确保高质量可执行性
- **严格质量过滤**: 22.7%保留率，确保高质量输出
- **类Text2SQL流程**: 更贴近实际系统工作原理

## Pipeline架构

### 整体流程图

```
CSpider数据库
    ↓
1. 数据库合并 (database_merge)
    ↓
2. 注释生成 (add_database_comments)
    ↓
3. 表总结生成 (generate_table_summaries)
    ↓
4. 向量相似性搜索 (vector_table_similarity)
    ↓
5. SQLite函数匹配 (match_sqlite_functions)
    ↓
6. SQL合成 (sql_synthesis)
    ↓
6.5. SQL修正 (sql_correction)
    ↓
7. 问题生成 (question_synthesis)
    ↓
8. 查询匹配验证 (sql_query_match_validation)
    ↓
最终训练数据
```

## 8.5个递进步骤详解

### 第1步：数据库合并 (Database Merge)
**目的**: 将CSpider数据集中的166个SQLite数据库合并成统一数据库

**输入**:
- CSpider/database/下的166个独立SQLite数据库文件

**输出**:
- `merged_cspider.sqlite` - 统一的合并数据库
- 合并统计报告和日志

**关键功能**:
- 解决表名冲突(添加数据库名前缀)
- 保持外键关系完整性
- 生成详细的合并日志

### 第2步：数据库注释生成 (Add Database Comments)
**目的**: 为数据库中的表和字段生成中文语义注释

**输入**:
- `merged_cspider.sqlite`

**输出**:
- 带中文注释的DDL语句
- 表和字段语义信息

**关键功能**:
- 基于表名、字段名、样例数据生成语义注释
- 使用LLM生成自然的中文业务注释
- 采用SQLite兼容的注释格式

### 第3步：表总结生成 (Generate Table Summaries)
**目的**: 为每个表生成业务总结和上下文信息

**输入**:
- 带注释的DDL数据

**输出**:
- 表级别的业务总结
- 字段功能分组描述

**关键功能**:
- 生成简洁的表用途描述
- 识别关键业务实体和关系
- 为向量搜索提供语义基础

### 第4步：向量表相似性搜索 (Vector Table Similarity)
**目的**: 使用向量化方法找到语义相似的表

**输入**:
- 表总结信息

**输出**:
- 每个表的最相似5个表
- 表向量表示

**关键功能**:
- 使用嵌入模型生成表向量
- 基于余弦相似度找相似表
- 支持多种向量模型(HuggingFace, vLLM)

### 第5步：SQLite函数匹配 (Match SQLite Functions)
**目的**: 为相似表匹配合适的SQLite函数

**输入**:
- 表相似性结果
- SQLite函数库(OmniSQL)

**输出**:
- 每个表匹配的函数列表
- 函数使用说明和示例

**关键功能**:
- 基于表结构匹配相关函数
- 生成函数使用场景描述
- 智能函数组合推荐

### 第6步：SQL合成 (SQL Synthesis)
**目的**: 基于丰富上下文生成多样化SQL查询

**输入**:
- 带注释的DDL + 表总结 + 相似表 + 匹配函数

**输出**:
- 不同复杂度的SQL查询
- 查询业务意图说明

**关键功能**:
- 生成简单到复杂的各类查询
- 结合函数使用和表关系
- 覆盖主要SQL操作类型
- 支持多种复杂度等级（简单、适中、复杂、高度复杂）

**模型配置**:
- 主要模型：**Qwen3-Coder-30B-A3B-Instruct**（专门优化的代码生成模型）
- 相比通用模型，SQL生成成功率显著提升
- 建议使用简单和适中复杂度以获得更高成功率

### 第6.5步：SQL修正 (SQL Correction)
**目的**: 对SQL合成阶段生成的失败SQL语句进行智能修正

**输入**:
- SQL合成阶段生成的SQL语句
- 数据库执行错误信息
- 原始上下文信息（DDL、表总结等）

**输出**:
- 修正后的可执行SQL语句
- 修正日志和统计报告

**关键功能**:
- **执行验证**: 在数据库中实际执行SQL语句
- **错误分析**: 捕获和分析SQL执行错误
- **智能修正**: 基于错误信息进行针对性修正
- **迭代优化**: 多轮修正直到SQL可执行

**修正策略**:
- 使用 **Qwen3-Coder-30B-A3B-Instruct** 模型进行修正
- 结合具体错误信息生成修正方案
- 保留原始查询意图的同时修复语法和逻辑错误

**性能数据**:
- 初期使用 qwen3-30B-A3B：32057条数据中仅33条可执行（0.1%）
- 改用 Qwen3-Coder-30B-A3B-Instruct + 简化复杂度：4834条数据中4834条可执行
- SQL修正模块可进一步提升可执行率

### 第7步：问题生成 (Question Synthesis)
**目的**: 将SQL查询转换为自然语言中文问题

**输入**:
- SQL查询语句 + 上下文信息

**输出**:
- 多种风格的中文问题
- 问句-SQL对

**关键功能**:
- 支持口语化、正式、命令式等风格
- 确保问题与SQL语义一致
- 生成多样化的问句表达

### 第8步：查询匹配验证 (SQL Query Match Validation)
**目的**: 验证问句-SQL对的质量和一致性

**输入**:
- 问句-SQL对

**输出**:
- 验证通过的最终训练数据
- 质量评估报告

**关键功能**:
- 多维度质量评估
- 语义一致性验证
- 自动筛选高质量数据

## 使用指南

### 环境要求
- Python 3.8+
- SQLite 3.x
- 足过16GB内存
- GPU支持(推荐，用于向量计算)

### 快速开始

1. **准备CSpider数据**
```bash
# 下载CSpider数据集到database_merge/full_CSpider目录
# 参考: https://drive.google.com/drive/folders/1TxCUq1ydPuBdDdHF3MkHT-8zixluQuLa
```

2. **执行Pipeline**
```bash
cd src/data_synthesis

# 按顺序执行8.5个步骤
cd database_merge/tools && python merge_sqlite_databases.py

cd ../../add_database_comments && python generate_ddl_comment_prompts.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py

cd ../../generate_table_summaries && python generate_ddl_summary_prompts.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py

# 继续执行向量相似性搜索、函数匹配等步骤
cd ../../vector_table_similarity/vector && python huggingface_embeddings.py
cd ../retrieve && python vector_search_engine.py
cd .. && python retrieve_similar_tables_by_summary.py

cd ../../match_sqlite_functions && python 构造schema适配的函数名称.py
python generate_sqlite_function_compatibility_prompts.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py
python 判断遗漏了哪些函数.py

# Step 6: SQL Synthesis
cd ../../sql_synthesis
python generate_sql_synthesis_prompt.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py

# Step 6.5: SQL Correction (可选 - 修复执行失败的SQL)
cd ../sql_correction
# 注意：此步骤仅对执行失败的SQL运行
python generate_correction_prompts.py      # 生成包含错误信息的修正提示
python generate_llm_responses.py.py        # 调用LLM进行SQL修正
python postprocess_llm_responses.py        # 清理修正后的SQL
python finalize_sql_outputs.py             # 验证修正后的SQL

# Step 7: Question Synthesis
cd ../question_synthesis
python generate_question_synthesis_prompts_zh.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py

# Step 8: Query Validation (Final Step)
cd ../sql_query_match_validation
python generate_prompts_zh.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py
```

### 批量执行脚本
每个模块都有标准的4步执行模式：
1. `generate_*_prompts*.py` - 生成提示词
2. `generate_llm_responses.py.py` - 调用LLM生成
3. `postprocess_llm_responses.py` - 后处理结果
4. `finalize_*_outputs.py` - 生成最终输出

## 配置管理

### LLM配置
**SQL生成和修正推荐模型配置**：
```python
# SQL合成和修正步骤（推荐）
base_url = "http://192.168.2.3:42434/v1"
model_name = "Qwen3-Coder-30B-A3B-Instruct"  # 专门优化的代码生成模型
timeout = 60

# 其他步骤（通用任务）
base_url = "http://192.168.2.3:42434/v1"
model_name = "Qwen3-30B-A3B"  # 通用模型
timeout = 60
```

**模型性能对比**：
- **Qwen3-30B-A3B** (通用): 32057条数据中仅33条SQL可执行 (0.1%)
- **Qwen3-Coder-30B-A3B-Instruct** (代码专用): 12,844条数据中4834条SQL可执行 (37.6%执行率)

### 处理参数
- `max_workers = 4` - 并发数
- `batch_size = 100` - 批处理大小
- `retry_attempts = 3` - 重试次数

### SQL复杂度配置
**推荐配置**（基于测试结果）：
- **简单**: 基础查询，成功率高
- **适中**: 中等复杂度，平衡覆盖面和成功率
- **复杂**: 高级查询，成功率较低
- **高度复杂**: 最困难查询，成功率最低

**建议**: 为保证SQL可执行率，优先使用"简单"和"适中"复杂度等级。

## 输出结果

### 最终训练数据格式
**简化格式** (核心字段):
```json
{
  "id": "unique_pair_id",
  "question": "我想知道有多少个成年用户？",
  "sql_query": "SELECT COUNT(*) FROM users WHERE age > 18",
  "required_tables": ["users"],
  "required_columns": ["users.age"],
  "complexity_level": "简单",
  "similarity_score": 0.95
}
```

**完整格式** (包含所有上下文信息): 见下方"最终数据格式"章节

### 数据统计
**实际生产数据**:
- **初始生成**: 12,844 条 (4834 + 8010)
- **SQL可执行**: 4,834 条 (37.6%执行率)
- **最终保留**: 2,914 条 (2331 训练集 + 583 验证集)
- **整体保留率**: 22.7%
- **质量控制**: 严格的多层过滤机制

**原始数据基础**:
- **表数量**: 694个合并表
- **复杂度等级**: 简单、适中 (高成功率配置)
- **函数匹配**: Schema导向的精准匹配

## 目录结构

```
src/data_synthesis/
├── README.md                    # 总体说明文档
├── database_merge/             # 步骤1: 数据库合并
│   ├── tools/                  # 合并工具
│   ├── full_CSpider/           # CSpider原始数据
│   ├── output/                 # 合并结果
│   └── reports/                # 分析报告
├── add_database_comments/       # 步骤2: 注释生成
├── generate_table_summaries/    # 步骤3: 表总结
├── vector_table_similarity/     # 步骤4: 向量相似性
├── match_sqlite_functions/      # 步骤5: 函数匹配
├── sql_synthesis/              # 步骤6: SQL合成
├── sql_correction/             # 步骤6.5: SQL修正
├── question_synthesis/         # 步骤7: 问题生成
└── sql_query_match_validation/ # 步骤8: 验证
```

## 技术创新点

### 1. 企业级数据源优势
**与OmniSQL对比**:
- **OmniSQL**: Web Tables → Synthetic Databases (网络表格 → 合成数据库)
- **本方案**: Real Private Databases → Enhanced Context (真实私有数据库 → 增强上下文)

**优势**:
- 数据隐私保护，不依赖外部Web数据
- 真实业务逻辑，贴近企业实际需求
- 数据质量有保障，避免合成数据偏差

### 2. Schema导向的函数匹配
**传统方法** (OmniSQL): 随机函数选择
- 从SQLite函数词典随机选择
- 可能生成不适用当前schema的函数

**本方案**: Schema引导的精准匹配
- 基于表结构智能匹配适用函数
- 考虑字段类型和表关系约束
- 更高的函数使用准确性

### 3. 倒序生成策略
**传统Text2SQL**: Question → SQL
**本方案**: SQL → Question
- 确保SQL的可执行性 (高执行率)
- 保证Question与SQL的语义一致性
- 更好控制SQL复杂度和质量

### 4. 类Text2SQL系统的生成流程
**实际系统**: Query → Embedding → 相似表 → SQL

**本方案**: 表 → 相似表检索 → 函数匹配 → SQL → Question

这种设计更贴近实际Text2SQL系统的工作原理，生成的数据更适合模型训练。

## 与OmniSQL详细对比

### 论文参考
**OmniSQL: Synthesizing High-quality Text-to-SQL Data at Scale**
- 论文链接: https://arxiv.org/pdf/2503.02240v2

### 核心差异

| 维度 | OmniSQL | 本方案 |
|------|---------|--------|
| **数据来源** | Web表格 | 私有数据库 |
| **数据库构建** | 合成模拟 | 真实业务 |
| **函数选择** | 随机选择 | Schema匹配 |
| **生成流程** | Database → SQL → Question | 表 → 相似表 → 函数 → SQL → Question |
| **质量控制** | 基础验证 | 多层过滤 |


### 性能对比
**OmniSQL** (基于论文):
- 依赖Web表格质量和覆盖度
- 函数使用可能不准确

**本方案** (实际数据):
- SQL可执行率: 37.6% (4834/12844)
- 数据质量保留率: 22.7% (严格过滤)
- 企业适配性: 优秀

## 数据质量与过滤策略

### 多层过滤机制

**第一层: SQL执行验证**
- 在数据库中实际执行SQL
- 过滤语法错误和逻辑错误

**第二层: 需求匹配度评估**
- 评估SQL与业务需求的相关性
- 使用相似度计算和规则匹配

**第三层: 语义一致性验证**
- 验证Question与SQL的语义对应
- 多维度质量评分

### 过滤效果统计
```
初始生成: 12,844 条
  ↓ SQL执行验证
中间数据: ~8,000 条
  ↓ 需求匹配度过滤
中间数据: ~4,000 条
  ↓ 语义一致性验证
最终数据: 2,914 条 (22.7% 保留率)
```

### 最终数据格式

**合成数据的完整结构**:
```json
{
  "table_name": "表名称",
  "create_sql": "CREATE TABLE语句",
  "sample_data": [
    {"col1": "value1", "col2": "value2"},
    {"col1": "value3", "col2": "value4"},
    {"col1": "value5", "col2": "value6"}
  ],
  "annotated_ddl": "带注释的DDL语句",
  "table_summary": "表业务总结",
  "similar_tables": [
    {
      "table_name": "相似表名",
      "create_sql": "相似表CREATE语句",
      "sample_data": [...],
      "annotated_ddl": "相似表注释DDL",
      "table_summary": "相似表总结"
    }
  ],
  "function_descriptions": {
    "函数名": "函数描述",
    "COUNT": "计算行数"
  },
  "prompt_context": {
    "filled": "填充的提示词上下文",
    "metadata": {
      "schema_str": "schema字符串",
      "sql_func_prompt": "SQL函数提示词",
      "db_value_prompt": "数据库值提示词"
    }
  },
  "synthesis_sql": "生成的SQL语句",
  "question_synthesis_metadata": {
    "prompt": "问题生成提示词",
    "style": "问题风格",
    "style_description": "风格描述",
    "engine": "使用的模型引擎",
    "sql": "SQL语句",
    "schema": "schema信息",
    "steps": "生成步骤",
    "guidelines": "指导原则",
    "output_format": "输出格式",
    "instruction": "指令"
  },
  "synthesis_question": "生成的问题",
  "static_requirement_matching": {
    "prompt": "需求匹配提示词",
    "sql": "SQL语句",
    "query": "查询语句",
    "schema": "schema信息"
  }
}
```

**最外层字段说明**:
- `table_name`: 当前处理的表名
- `create_sql`: 表的创建SQL语句
- `sample_data`: 3条示例数据
- `annotated_ddl`: 包含中文注释的DDL
- `table_summary`: 表级别的业务总结
- `similar_tables`: 最多5个相似表的信息列表
- `function_descriptions`: 匹配的SQLite函数字典
- `prompt_context`: 提示词上下文信息
- `synthesis_sql`: 生成的SQL查询
- `question_synthesis_metadata`: 问题生成的元数据
- `synthesis_question`: 最终生成的中文问题
- `static_requirement_matching`: 需求匹配度评估信息

## 技术配置详情

### 向量相似性搜索配置
```python
# 实际使用配置
embedding_model = "nlp_gte_sentence-embedding_chinese-small"
similarity_cutoff = 0.7
max_similar_tables = 5
# 每个表检索最多5个相似表，且相似度在0.7以上
```

### 函数匹配策略
- **函数词典规模**: 150+ SQLite函数
- **匹配规则**: 基于字段类型、表关系、业务场景
- **组合优化**: 支持函数组合使用场景

### 训练集/验证集划分
- **训练集**: 2,331 条 (80%)
- **验证集**: 583 条 (20%)
- **划分策略**: 基于表类型和SQL复杂度的分层抽样
- **去重处理**: 确保无数据泄露

