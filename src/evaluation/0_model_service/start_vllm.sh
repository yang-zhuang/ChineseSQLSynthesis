#!/bin/bash

# 启动带LoRA的vLLM服务
python -m vllm.entrypoints.openai.api_server \
    --model /root/autodl-tmp/modelscope/Qwen3-0.6B \
    --served-model-name Qwen3-0.6B \
    --enable-lora \
    --lora-modules dapo-Qwen3-0.6B=/root/Code/ChineseSQLSynthesis/outputs/dapo-Qwen3-0.6B/checkpoint-4660 \
    --gpu-memory-utilization 0.85 \
    --max-model-len 10240 \
    --max-num-seqs 50 \
    --port 8000