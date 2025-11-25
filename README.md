# ChineseSQLSynthesis - 企业级中文Text-to-SQL数据合成与训练系统

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![PyTorch](https://img.shields.io/badge/pytorch-2.0%2B-orange.svg)](https://pytorch.org)
[![CUDA](https://img.shields.io/badge/cuda-11.0%2B-green.svg)](https://developer.nvidia.com/cuda-zone)

**基于私有数据库的企业级中文Text-to-SQL数据合成与DAPO微调训练系统**

[📖 文档](./src/README.md) | [🚀 快速开始](#快速开始) | [🎯 特色功能](#核心特色) | [📊 效果展示](#性能效果)

</div>

## 项目概述

ChineseSQLSynthesis是一个完整的企业级中文Text-to-SQL解决方案，专为私有数据库环境设计。本项目创新性地结合了：

- **8.5步数据合成Pipeline**: 将私有数据库转换为高质量训练数据
- **DAPO强化学习微调**: 应用开源大规模LLM强化学习系统
- **双重评估体系**: SQL执行成功率 + 语义等价性评估

### 🎯 解决的核心问题

1. **企业数据隐私**: 基于私有数据库生成训练数据，无需外部依赖
2. **高质量数据**: 22.7%严格筛选保留率，确保训练数据质量
3. **执行可靠性**: 通过SQL执行验证确保生成语句可执行
4. **中文优化**: 专门针对中文Text-to-SQL任务的优化方案

## 🌟 核心特色

### 🔒 企业级数据安全
- **私有数据库驱动**: 完全基于内部数据，保护企业敏感信息
- **本地化部署**: 支持完全私有化部署，无云服务依赖
- **数据不出域**: 数据处理和模型训练全在本地环境

### 🚀 创新技术方案
- **Schema导向函数匹配**: 智能匹配SQLite函数，避免随机选择
- **倒序生成策略**: SQL → Question，确保100%可执行性验证
- **向量相似性检索**: 使用中文嵌入模型检索相似表
- **DAPO强化学习**: 应用先进的开源强化学习微调技术

### 📊 严格质量控制
- **多层过滤机制**: SQL执行 + 需求匹配 + 语义一致性
- **高精度筛选**: 12,844→2,914条，22.7%保留率
- **双重验证**: 执行成功率(90.39%) + 语义等价性(39.45%)

## 🏗️ 项目架构

```
ChineseSQLSynthesis/
├── README.md                          # 本文档 - 项目总览
├── CLAUDE.md                          # Claude Code使用指南
├── requirements.txt                   # Python依赖包
├── .gitignore                         # Git忽略文件
│
├── src/                               # 核心源代码
│   ├── README.md                      # 详细技术文档
│   ├── data_synthesis/                # 数据合成Pipeline (8.5步骤)
│   ├── evaluation/                    # 模型评估系统 (5步骤)
│   ├── training_data_processor/       # 训练数据预处理
│   ├── scripts/                       # 训练脚本
│   ├── rewards/                       # DAPO奖励函数设计
│   └── training/                      # 模型训练模块
│
├── scripts/                           # 项目级脚本
│   └── train_dapo_lora.sh             # DAPO LoRA微调主脚本
│
├── evaluation_results/                # 评估结果存储
│   ├── 4_final_metrics/               # 最终评估指标
│   ├── 1_sql_generation/              # SQL生成结果
│   ├── 2_execution_validation/        # 执行验证结果
│   └── 3_semantic_evaluation/         # 语义评估结果
│
├── data/                              # 数据存储目录
│   └── ...                            # CSpider数据集及中间结果
│
└── outputs/                           # 输出结果目录
    ├── dapo-Qwen3-0.6B/               # DAPO微调后的LoRA模型
    │   └── checkpoint-4660/           # 预训练微调模型检查点
    └── ...                            # 其他训练和评估输出
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+

### 安装配置

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/ChineseSQLSynthesis.git
cd ChineseSQLSynthesis

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env  # 根据实际情况修改配置
```

### 🎯 选择您的使用场景

**场景一：直接评估预训练模型（推荐新手）**
- ✅ 已有训练好的LoRA模型：`outputs/dapo-Qwen3-0.6B/checkpoint-4660`
- ✅ 无需重新训练，开箱即用
- 📖 **详细指南** → [评估系统使用说明](./src/evaluation/README.md)

**场景二：生成新的训练数据**
- 📊 需要为您的数据库生成训练数据
- 🔄 完整的8.5步数据合成Pipeline
- 📖 **详细指南** → [数据合成Pipeline说明](./src/data_synthesis/README.md)

**场景三：从头开始完整训练**
- 🔧 数据合成 → 预处理 → DAPO微调 → 效果评估
- ⚙️ 适合研究人员和深度定制需求
- 📖 **完整技术文档** → [src/README.md](./src/README.md)

---

#### 🔥 最常用路径

**如果您只想快速评估效果：**
```bash
# 1. 查看评估流程
cat src/evaluation/README.md

# 2. 按指南启动评估
cd src/evaluation
# 按文档中的5步骤执行
```

**如果您需要生成新数据：**
```bash
# 1. 了解数据合成流程
cat src/data_synthesis/README.md

# 2. 开始数据合成
cd src/data_synthesis
# 按文档中的8.5步骤执行
```

**如果您需要完整训练：**
```bash
# 1. 查看完整技术文档
cat src/README.md

# 2. 按文档执行完整流程
```

## 📈 性能效果

### 数据合成成果

| 指标 | 数值 | 说明 |
|------|------|------|
| **初始生成** | 12,844条 | 4834 + 8010条数据 |
| **SQL可执行** | 4,834条 | 37.6%执行率 |
| **最终保留** | 2,914条 | 2331训练集 + 583验证集 |
| **整体保留率** | 22.7% | 严格质量控制 |

### DAPO微调效果

**项目提供的预训练模型**: `outputs/dapo-Qwen3-0.6B/checkpoint-4660`

| 指标 | 基础模型 | DAPO微调 | 性能提升 |
|------|----------|----------|----------|
| **SQL执行成功率** | 68.27% | 90.39% | **+22.12%** |
| **语义等价性** | 33.45% | 39.45% | **+6.00%** |
| **基础模型** | Qwen3-0.6B | Qwen3-0.6B+LoRA | 思考模式 |
| **训练样本** | - | 2,331条 | 高质量合成数据 |
| **检查点** | - | checkpoint-4660 | 可直接使用 |

### 与基线方案对比

| 维度 | OmniSQL | 本方案 | 优势 |
|------|---------|--------|------|
| **数据来源** | Web表格 | 私有数据库 | 企业适配 |
| **函数选择** | 随机选择 | Schema匹配 | 精准匹配 |
| **SQL执行率** | 未公开 | 37.6% | 可验证 |
| **企业部署** | 困难 | 友好 | 私有化 |

## 🛠️ 技术配置

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

### DAPO奖励函数
```python
# 多维度奖励函数组合
rewards = [
    "rewards.execution_reward.sql_execution_reward",           # SQL执行奖励
    "rewards.sql_similarity_rewards.sql_word_reward",         # SQL相似性奖励
    "rewards.sql_similarity_rewards.sql_word_penalty",        # SQL相似性惩罚
    "rewards.format_rewards.think_tag_penalty",               # 格式惩罚
    "rewards.format_rewards.valid_sql_markdown_reward",       # 格式奖励
    "rewards.base_rewards.get_soft_overlong_punishment_medium" # 长度惩罚
]
```

## 📚 详细文档

### 核心文档
- **[技术总览](./src/README.md)** - 完整的技术架构和使用指南
- **[数据合成Pipeline](./src/data_synthesis/README.md)** - 8.5步数据合成流程详解
- **[DAPO训练评估](./src/evaluation/README.md)** - 模型训练效果评估报告

### 技术论文
- **[OmniSQL](https://arxiv.org/pdf/2503.02240v2)** - Synthesizing High-quality Text-to-SQL Data at Scale
- **[DAPO](https://arxiv.org/abs/2503.14476)** - An Open-Source LLM Reinforcement Learning System at Scale

## 🎯 应用场景

### 企业级应用
- **开箱即用**: 使用项目提供的预训练模型 `outputs/dapo-Qwen3-0.6B/checkpoint-4660`
- **私有化Text-to-SQL系统**: 基于企业内部数据库训练专用模型
- **业务智能分析**: 自动化SQL查询生成，提升数据分析效率
- **智能数据检索**: 企业内部智能查询助手
- **数据增强服务**: 为现有NLP系统提供高质量训练数据

### 技术研究
- **中文NLP研究**: 中文Text-to-SQL技术创新
- **强化学习应用**: DAPO在生成任务中的应用研究
- **数据合成方法**: 高质量训练数据生成技术研究
- **企业AI落地**: 私有环境下的AI应用实践

## 🔧 开发指南

### 自定义奖励函数
```python
# 在rewards目录下创建新的奖励函数
# src/rewards/your_reward.py

def compute_reward(generated_sql, target_sql, execution_result):
    """
    自定义奖励函数逻辑
    """
    reward = 0.0

    # 实现你的奖励逻辑
    # ...

    return reward
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

### 开发流程
1. Fork项目到个人仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 代码规范
- 遵循PEP 8 Python代码规范
- 添加详细的中文注释和文档
- 确保所有代码都有完整的错误处理
- 运行测试确保通过

## 🐛 常见问题

<details>
<summary><strong>Q: 内存不足怎么办？</strong></summary>

**A**: 可以通过以下方式减少内存使用：
- 减少批处理大小：`batch_size = 8`
- 减少并发数：`max_workers = 2`
- 使用梯度检查点：`gradient_checkpointing=True`
</details>

<details>
<summary><strong>Q: 模型训练很慢怎么办？</strong></summary>

**A**: 优化训练速度的方法：
- 使用多GPU：调整`CUDA_VISIBLE_DEVICES`
- 开启混合精度：`fp16=True`
- 使用DeepSpeed优化器
- 增加数据加载的worker数量
</details>

<details>
<summary><strong>Q: 数据合成失败怎么办？</strong></summary>

**A**: 检查以下几点：
- 确认LLM API服务正常运行
- 检查数据库文件权限
- 查看详细日志文件定位问题
- 使用断点续传功能重新开始
</details>

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- **CSpider数据集**: 提供了高质量的中文Text-to-SQL基准数据
- **Qwen模型团队**: 提供了优秀的中文预训练模型
- **DAPO论文作者**: 提供了创新的强化学习方法
- **开源社区**: 所有为本项目做出贡献的开发者

## 📞 联系我们

- **项目主页**: https://github.com/your-repo/ChineseSQLSynthesis
- **问题反馈**: [GitHub Issues](https://github.com/your-repo/ChineseSQLSynthesis/issues)
- **功能建议**: [GitHub Discussions](https://github.com/your-repo/ChineseSQLSynthesis/discussions)
- **技术交流**: 我们的技术交流群

---

<div align="center">

**如果这个项目对您有帮助，请给我们一个⭐️！**

Made with ❤️ for Chinese NLP Community

</div>