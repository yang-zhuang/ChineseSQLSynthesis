# ChineseSQLSynthesis - 中文Text-to-SQL数据合成与训练系统

## 项目概述

ChineseSQLSynthesis是一个企业级中文Text-to-SQL数据合成与模型训练系统。本项目通过创新的8.5步Pipeline，将私有数据库转换为高质量的中文问句-SQL对训练数据，并应用DAPO（An Open-Source LLM Reinforcement Learning System at Scale）技术进行模型微调和效果评估。

## 🎯 核心特色

### 数据合成Pipeline
- **企业级数据源**: 基于私有数据库，保护数据隐私
- **Schema导向函数匹配**: 智能匹配适用函数，非随机选择
- **倒序生成策略**: SQL → Question，确保高质量可执行性
- **严格质量过滤**: 22.7%保留率，确保高质量输出
- **类Text2SQL流程**: 更贴近实际系统工作原理

### 模型训练与评估
- **DAPO微调**: 应用开源大规模LLM强化学习系统
- **双重评估**: SQL执行成功率 + 语义等价性
- **思考模式**: 提升模型推理能力
- **企业友好**: 支持私有化部署

## 📁 项目结构

```
src/
├── README.md                           # 本文档 - 项目总体介绍
├── data_synthesis/                     # 数据合成Pipeline (8.5步骤)
│   ├── README.md                       # 详细的数据合成文档
│   ├── database_merge/                 # 步骤1: 数据库合并
│   ├── add_database_comments/          # 步骤2: 注释生成
│   ├── generate_table_summaries/       # 步骤3: 表总结生成
│   ├── vector_table_similarity/        # 步骤4: 向量相似性搜索
│   ├── match_sqlite_functions/         # 步骤5: SQLite函数匹配
│   ├── sql_synthesis/                  # 步骤6: SQL合成
│   ├── sql_correction/                 # 步骤6.5: SQL修正
│   ├── question_synthesis/             # 步骤7: 问题生成
│   └── sql_query_match_validation/     # 步骤8: 查询匹配验证
├── evaluation/                         # 模型评估系统
│   ├── README.md                       # DAPO训练效果评估文档
│   ├── 0_model_service/                # 模型服务启动
│   ├── 1_sql_generation/               # SQL生成评估
│   ├── 2_execution_validation/         # SQL执行验证
│   ├── 3_semantic_evaluation/          # 语义等价性评估
│   └── 4_metrics_aggregation/          # 指标聚合
├── training_data_processor/            # 训练数据预处理
│   └── generate_sql_training_data.py   # 合成数据转微调格式
├── scripts/                            # 训练脚本
│   └── train_dapo_lora.sh              # DAPO LoRA微调脚本
├── rewards/                            # DAPO奖励函数设计
│   ├── execution_reward.py             # SQL执行奖励
│   ├── sql_similarity_rewards.py       # SQL相似性奖励/惩罚
│   ├── format_rewards.py               # 格式奖励/惩罚
│   └── base_rewards.py                 # 基础奖励函数
└── training/                           # 模型训练模块 (待扩展)
    ├── README.md                       # 训练流程文档
    ├── dapo_training/                  # DAPO微调训练
    └── model_evaluation/               # 训练效果评估

# 项目根目录
evaluation_results/                     # 评估结果存储
├── 4_final_metrics/                    # 最终评估指标
├── 1_sql_generation/                     # SQL生成结果
├── 2_execution_validation/               # 执行验证结果
└── 3_semantic_evaluation/                # 语义评估结果
```

## 🚀 快速开始

### 1. 环境准备
```bash
# 安装Python依赖
pip install -r requirements.txt

# 确保GPU环境支持（推荐）
nvidia-smi  # 检查GPU状态
```

### 2. 数据合成Pipeline
```bash
# 进入数据合成目录
cd src/data_synthesis

# 按顺序执行8.5个步骤
# 1. 数据库合并
cd database_merge/tools && python merge_sqlite_databases.py

# 2-8步按README.md中的详细说明执行
```

### 3. 数据预处理（训练前必需）
```bash
# 进入数据预处理目录
cd src/training_data_processor

# 将合成的数据转换为微调格式
python generate_sql_training_data.py
```

### 4. 模型训练（DAPO微调）
```bash
# 进入脚本目录
cd scripts

# 执行DAPO LoRA微调训练
sh train_dapo_lora.sh

# 注意：需要修改脚本中的相关配置
# - 模型地址：修改base_model_path
# - 数据集地址：修改training_data_path
# - 输出地址：修改output_dir
```

### 5. 模型评估
```bash
# 进入评估目录
cd src/evaluation

# 按顺序执行5个评估步骤
# 1. 启动模型服务
cd 0_model_service && sh start_vllm.sh

# 2-5步按README.md中的详细说明执行
```

## 📊 核心成果

### 数据合成成果
- **初始生成**: 12,844 条 (4834 + 8010)
- **SQL可执行**: 4,834 条 (37.6%执行率)
- **最终保留**: 2,914 条 (2331训练集 + 583验证集)
- **整体保留率**: 22.7%

### 模型训练效果
- **SQL执行成功率**: 68.27% → 90.39% (+22.12%)
- **语义等价性**: 33.45% → 39.45% (+6.00%)
- **基础模型**: Qwen3-0.6B
- **微调方法**: DAPO开源强化学习系统

## 🔧 技术配置

### 数据合成配置
```python
# 向量相似性搜索
embedding_model = "nlp_gte_sentence-embedding_chinese-small"
similarity_cutoff = 0.7
max_similar_tables = 5

# SQL生成模型
base_url = "http://192.168.2.3:42434/v1"
model_name = "Qwen3-Coder-30B-A3B-Instruct"
```

### 模型训练配置
```python
# 基础模型
base_model = "Qwen3-0.6B"
training_data = 2,331条训练样本
optimization_method = "DAPO (An Open-Source LLM Reinforcement Learning System at Scale)"

# 训练脚本路径
train_script = "scripts/train_dapo_lora.sh"
data_processor = "training_data_processor/generate_sql_training_data.py"
```

### DAPO奖励函数设计
本项目采用多维度的奖励函数组合，确保训练效果的全面优化：

#### 1. 执行奖励 (Execution Rewards)
```python
# SQL执行成功奖励
rewards.execution_reward.sql_execution_reward
```
**功能**: 奖励生成SQL能够成功在数据库中执行

**奖励值**: 执行成功 +1.0，执行失败 -1.0

#### 2. SQL相似性奖励 (SQL Similarity Rewards)
```python
# SQL词汇匹配奖励
rewards.sql_similarity_rewards.sql_word_reward

# SQL词汇匹配惩罚
rewards.sql_similarity_rewards.sql_word_penalty
```
**功能**: 评估生成SQL与目标SQL的词汇相似度

**计算方法**:
- **奖励**: 关键词匹配（SELECT、FROM、WHERE等）
- **惩罚**: 缺失关键词或错误关键词

#### 3. 格式奖励 (Format Rewards)
```python
# 思考标签格式惩罚
rewards.format_rewards.think_tag_penalty

# 有效SQL Markdown格式奖励
rewards.format_rewards.valid_sql_markdown_reward
```
**功能**: 确保输出格式符合预期规范
**标准**:
- **思考标签**: 要求使用标准的思考标签格式<think>`标签
- **SQL格式**: 要求使用Markdown代码块格式（```sql ... ```）

#### 4. 基础奖励 (Base Rewards)
```python
# 软性过长惩罚（中等强度）
rewards.base_rewards.get_soft_overlong_punishment_medium
```
**功能**: 防止生成过长或冗余的SQL语句
**惩罚机制**: 根据SQL长度进行渐进式惩罚

**设计理念**:
1. **执行优先**: SQL可执行性是最重要指标
2. **语义一致**: 确保与目标SQL的语义相似性
3. **格式规范**: 维持输出格式的一致性
4. **长度控制**: 避免生成冗余内容

### 评估配置
```python
# 生成模型（思考模式）
generation_model = "Qwen3-0.6B"
thinking_mode = True

# 评估模型（语义等价性）
judge_model = "Qwen3-30B-A3B"
judge_mode = "thinking"
```

## 📚 详细文档

### 核心模块文档
- **[数据合成Pipeline](./data_synthesis/README.md)**: 完整的8.5步数据合成流程说明
- **[DAPO训练评估](./evaluation/README.md)**: 详细的模型训练效果评估报告

### 技术参考论文
- **[OmniSQL: Synthesizing High-quality Text-to-SQL Data at Scale](https://arxiv.org/pdf/2503.02240v2)**: 数据合成方法参考
- **[DAPO: An Open-Source LLM Reinforcement Learning System at Scale](https://arxiv.org/abs/2503.14476)**: 微调训练方法参考


## 🛠️ 开发指南

### 添加新模块
1. 在对应目录下创建新的子目录
2. 编写标准的4步处理脚本（生成提示词 → LLM调用 → 后处理 → 最终输出）
3. 更新相应的README.md文档
4. 添加到主要的执行流程中

### 扩展数据源
1. 在`database_merge`目录添加新的数据源适配器
2. 更新数据格式转换逻辑
3. 重新运行数据合成Pipeline
4. 更新评估数据集

### 自定义评估指标
1. 在`evaluation`目录添加新的评估模块
2. 实现指标计算逻辑
3. 集成到指标聚合流程
4. 更新评估报告格式

## 🔍 技术创新点

### 数据合成创新
1. **企业数据驱动**: 首个基于私有数据库的Text-to-SQL数据合成方案
2. **Schema函数匹配**: 智能匹配SQLite函数，避免随机选择
3. **倒序生成策略**: SQL→Question确保可执行性和一致性
4. **多层质量过滤**: 22.7%严格筛选保留率确保高质量

### 训练评估创新
1. **DAPO应用**: 首个将DAPO应用于Text-to-SQL任务的企业级方案
2. **双重评估**: SQL执行成功率 + 语义等价性的综合评估
3. **思考模式**: 在生成和评估中启用模型思考能力
4. **端到端验证**: 从数据合成到模型训练的完整验证流程

## 📈 性能优势

### 与OmniSQL对比
| 维度 | OmniSQL | 本方案 |
|------|---------|--------|
| **数据来源** | Web表格 | 私有数据库 |
| **函数选择** | 随机选择 | Schema匹配 |
| **生成流程** | Database → SQL → Question | 表 → 相似表 → 函数 → SQL → Question |
| **企业适配** | 通用研究 | 企业应用 |

### 实际应用效果
- **数据隐私**: 100%基于内部数据，无外部依赖
- **业务相关性**: 真实业务场景，贴近实际需求
- **质量可控**: 严格的多层过滤机制
- **部署友好**: 支持私有化部署，无云服务依赖

## 🤝 贡献指南

### 开发流程
1. Fork本项目到个人仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

### 代码规范
- 遵循PEP 8 Python代码规范
- 添加详细的中文注释
- 确保所有脚本都有完整的错误处理
- 更新相应的README.md文档

### 测试要求
- 所有新增功能都需要有测试用例
- 确保向后兼容性
- 在多个环境下测试通过

## 📞 技术支持

### 常见问题
1. **模型加载失败**: 检查模型路径和GPU内存
2. **数据合成中断**: 查看日志文件，使用断点续传
3. **评估服务连接失败**: 确认vLLM服务状态
4. **内存不足**: 调整批处理大小和并发数

### 联系方式
- **技术文档**: 查看各子模块的详细README.md
- **问题反馈**: 通过GitHub Issues提交
- **功能建议**: 通过GitHub Discussions讨论

## 📄 许可证

本项目遵循相应的开源许可证，详见LICENSE文件。