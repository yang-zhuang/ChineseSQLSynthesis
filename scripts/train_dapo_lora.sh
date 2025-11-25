#!/bin/bash
# ==============================
# GRPO 训练脚本 - Qwen3-0.6B 模型
# 用于SQL生成任务的强化学习训练
# ==============================

# ------------------------------
# 数据配置
# ------------------------------
# 训练数据集路径（使用绝对路径）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATASET_PATH="data/train.jsonl"
# 输入提示的最大长度
MAX_PROMPT_LENGTH=6500
# 生成结果的最大长度
MAX_COMPLETION_LENGTH=1024

# ------------------------------
# 模型配置
# ------------------------------
# 基础模型路径 (注意：Windows路径使用正斜杠或双反斜杠)
#MODEL_PATH="/mnt/d/modelscope/Qwen3-0.6B-GPTQ-Int8"
MODEL_PATH="/root/autodl-tmp/modelscope/Qwen3-0.6B"
# 计算精度 (bfloat16/float16/float32)
DTYPE="bfloat16"
# 是否使用PEFT参数高效微调
USE_PEFT="--use_peft"

#############
vllm_gpu_memory_utilization=0.5
vllm_mode='colocate'
use_vllm="--use_vllm"
logging_steps=10
load_in_4bit="--load_in_4bit"
use_liger_kernel="--use_liger_kernel"
num_train_epochs=1
save_total_limit=2
save_steps=50
save_strategy="steps"
########

# ------------------------------
# 训练配置
# ------------------------------
# 总训练迭代次数
NUM_ITERATIONS=2
# 每次迭代生成的样本数
NUM_GENERATIONS=4
# 每次生成的优化步数
STEPS_PER_GENERATION=4
# 梯度累积步数
GRADIENT_ACCUMULATION_STEPS=2
# 每设备批大小
BATCH_SIZE=2
# 损失函数类型
LOSS_TYPE="dapo"
# 重要性采样级别
SAMPLING_LEVEL="token"

# ------------------------------
# 优化器配置
# ------------------------------
# 学习率
LEARNING_RATE=1e-5
# KL散度控制参数 (低)
EPSILON=0.2
# KL散度控制参数 (高)
EPSILON_HIGH=0.28
# 优势函数平滑系数
BETA=0.0

# ------------------------------
# 输出配置
# ------------------------------
# 模型输出目录（使用相对路径）
OUTPUT_DIR="outputs/dapo-Qwen3-0.6B"
# 是否记录生成的完整内容
LOG_COMPLETIONS="--log_completions"

# ==============================
# 路径调试信息
# ==============================
echo "🔧 调试信息:"
echo "📁 脚本目录: $SCRIPT_DIR"
echo "📁 项目根目录: $PROJECT_ROOT"
echo "📄 数据文件路径: $PROJECT_ROOT/$DATASET_PATH"
echo "📄 数据文件是否存在: $(test -f "$PROJECT_ROOT/$DATASET_PATH" && echo "✅ 存在" || echo "❌ 不存在")"
echo "📤 输出目录: $PROJECT_ROOT/$OUTPUT_DIR"
echo ""

# ==============================
# 执行训练命令
# ==============================
#num_train_epochs=1
 # save_total_limit=2
 # save_steps=10
 # save_strategy="steps"

cd "$PROJECT_ROOT" && PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python src/training/grpo.py \
    --dataset_name "$DATASET_PATH" \
    --model_name_or_path "$MODEL_PATH" \
    --output_dir "$OUTPUT_DIR" \
    --max_prompt_length "$MAX_PROMPT_LENGTH" \
    --max_completion_length "$MAX_COMPLETION_LENGTH" \
    --vllm_mode "$vllm_mode" \
    --vllm_gpu_memory_utilization "$vllm_gpu_memory_utilization" \
    --num_train_epochs "$num_train_epochs" \
    --save_total_limit "$save_total_limit" \
    --save_steps "$save_steps" \
    --save_strategy "$save_strategy" \
    --logging_steps "$logging_steps" \
    $load_in_4bit \
    $use_vllm \
    $USE_PEFT \
    $LOG_COMPLETIONS \
    --learning_rate "$LEARNING_RATE" \
    --dtype "$DTYPE" \
    --per_device_train_batch_size "$BATCH_SIZE" \
    --num_generations "$NUM_GENERATIONS" \
    --gradient_accumulation_steps "$GRADIENT_ACCUMULATION_STEPS" \
    --steps_per_generation "$STEPS_PER_GENERATION" \
    --epsilon "$EPSILON" \
    --epsilon_high "$EPSILON_HIGH" \
    --beta "$BETA" \
    --reward_funcs "rewards.execution_reward.sql_execution_reward" "rewards.sql_similarity_rewards.sql_word_reward" "rewards.sql_similarity_rewards.sql_word_penalty" "rewards.format_rewards.think_tag_penalty" "rewards.format_rewards.valid_sql_markdown_reward" "rewards.base_rewards.get_soft_overlong_punishment_medium" \
    --num_iterations "$NUM_ITERATIONS" \
    --loss_type "$LOSS_TYPE" \
    --importance_sampling_level "$SAMPLING_LEVEL" \
    --report_to tensorboard