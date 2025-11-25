# 向量表相似性搜索模块 (Vector Table Similarity)

## 模块概述

向量表相似性搜索模块是text-to-sql训练数据合成pipeline的第四步。该模块基于生成的表总结信息，使用向量嵌入模型为每个表生成语义向量，并通过向量相似性搜索为每个表找到最相似的5个表，为后续的SQL函数匹配提供语义相关的上下文信息。

## 主要功能

### 1. 向量嵌入生成
- **输入**: 包含业务总结的表信息
- **输出**: 每个表的语义向量表示
- **功能**: 将表的业务总结转换为高维向量，捕捉语义信息

### 2. 相似性搜索
- **输入**: 所有表的向量表示
- **输出**: 每个表的最相似5个表列表
- **功能**: 基于余弦相似度找到语义相关的表

## 执行步骤

### 步骤1: 向量化表总结信息
```bash
cd vector
python huggingface_embeddings.py    # 使用HuggingFace模型
# 或者
python vllm_embeddings.py          # 使用vLLM模型
```

### 步骤2: 构建向量搜索引擎
```bash
cd retrieve
python vector_search_engine.py     # 构建向量索引
```

### 步骤3: 执行相似性搜索
```bash
python retrieve_similar_tables_by_summary.py
```

## 核心脚本说明

### `vector/huggingface_embeddings.py`
使用HuggingFace模型生成向量嵌入：

**主要功能**:
- 加载预训练的中文文本嵌入模型
- 批量处理表总结文本
- 生成高质量的语义向量

### `vector/vllm_embeddings.py`
使用vLLM模型生成向量嵌入：

**主要功能**:
- 支持大模型的向量化推理
- 高性能的批量处理
- GPU加速的向量生成

### `retrieve/vector_search_engine.py`
向量搜索引擎实现：

**主要功能**:
- 构建向量索引(FAISS/Annoy等)
- 实现高效的相似性搜索
- 支持大规模向量检索

### `retrieve_similar_tables_by_summary.py`
主要的相似性搜索脚本：

**主要功能**:
- 读取表总结信息
- 生成向量表示
- 执行相似性搜索
- 输出相似表结果

## 数据结构

### 输入数据格式
```json
{
  "table_name": "表名",
  "business_summary": "业务总结文本",
  "main_features": ["主要特征"],
  "business_scenarios": ["业务场景"],
  "key_entities": ["关键实体"]
}
```

### 输出数据格式
```json
{
  "table_name": "当前表名",
  "table_vector": [0.1, 0.2, ...],  // 向量表示
  "similar_tables": [
    {
      "similar_table": "相似表名",
      "similarity_score": 0.85,
      "similarity_reason": "相似原因"
    }
  ],
  "vector_embedding_info": {
    "model_name": "使用的嵌入模型",
    "embedding_dimension": 768,
    "embedding_time": "2024-01-01T12:00:00Z"
  }
}
```

## 配置参数

### 向量模型配置
```python
# HuggingFace配置
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
BATCH_SIZE = 32
MAX_LENGTH = 512
DEVICE = "cuda"  # 或 "cpu"
```

### 搜索配置
```python
# 相似性搜索参数
TOP_K = 5                    # 返回最相似的K个表
SIMILARITY_THRESHOLD = 0.3   # 相似度阈值
VECTOR_DIMENSION = 768       # 向量维度
INDEX_TYPE = "faiss"         # 索引类型
```

## 输入输出

### 输入数据
```
# 输入：来自generate_table_summaries模块的JSONL文件
../generate_table_summaries/output/final_table_outputs.jsonl    # 表总结信息
```

### 输出数据
```
output/
├── table_vectors.jsonl       # 表向量表示
├── similarity_results.jsonl  # 相似性搜索结果
├── vector_index.faiss        # FAISS索引文件
├── similarity_report.json    # 相似性分析报告
└── embedding_statistics.json # 向量化统计信息
```

## 后续步骤

生成的表相似性结果将作为下一个模块`match_sqlite_functions`的输入，用于为相似的表找到适合的SQLite函数。