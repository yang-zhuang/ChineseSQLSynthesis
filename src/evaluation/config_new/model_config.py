"""
Model configuration settings
"""

# Text-to-SQL generation models
TEXT2SQL_MODELS = {
    "base_model": {
        "api_url": "http://localhost:8000/v1",
        "api_key": "token-abc123",
        "model_name": "Qwen3-0.6B",
        "max_tokens": 2048,
        "temperature": 0.1,
        "top_p": 0.9,
        "description": "Base model without fine-tuning"
    },
    "lora_model": {
        "api_url": "http://localhost:8000/v1",
        "api_key": "token-abc123",
        "model_name": "dapo-Qwen3-0.6B",
        "max_tokens": 2048,
        "temperature": 0.1,
        "top_p": 0.9,
        "description": "LoRA fine-tuned model"
    }
}

# vLLM service configuration
VLLM_SERVICE_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "base_model_path": "/path/to/base/model",  # 需要用户配置
    "lora_model_path": "/path/to/lora/model",  # 需要用户配置
    "gpu_memory_utilization": 0.8,
    "max_num_seqs": 128,
    "max_model_len": 4096,
    "tensor_parallel_size": 1
}

# vLLM startup script template
VLLM_STARTUP_COMMAND = """
python -m vllm.entrypoints.openai.api_server \\
    --model {base_model_path} \\
    --port {port} \\
    --host {host} \\
    --lora-modules lora={lora_model_path} \\
    --served-model-name {served_model_name} \\
    --gpu-memory-utilization {gpu_memory_utilization} \\
    --max-num-seqs {max_num_seqs} \\
    --max-model-len {max_model_len} \\
    --tensor-parallel-size {tensor_parallel_size}
"""