"""
Evaluation configuration settings
"""
import os
from pathlib import Path
from typing import Dict, List

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
EVALUATION_DIR = BASE_DIR / "src" / "evaluation"
RESULTS_DIR = BASE_DIR / "evaluation_results"

# Database configuration
DEFAULT_DB_PATH = BASE_DIR / "src/data_synthesis/database_merge/report/merged_cspider.sqlite"
DB_TIMEOUT_SECONDS = 2.0

# File paths configuration
DEFAULT_TEST_DATA_PATH = DATA_DIR / "test.jsonl"
DEFAULT_TRAIN_DATA_PATH = DATA_DIR / "train.jsonl"

# Results directory structure
RESULTS_CONFIG = {
    "sql_generation": {
        "base_dir": RESULTS_DIR / "1_sql_generation",
        "base_model": "base_model_predictions.jsonl",
        "lora_model": "lora_model_predictions.jsonl"
    },
    "execution_validation": {
        "base_dir": RESULTS_DIR / "2_execution_validation",
        "base_model": "base_model_execution_results.jsonl",
        "lora_model": "lora_model_execution_results.jsonl"
    },
    "semantic_evaluation": {
        "base_dir": RESULTS_DIR / "3_semantic_evaluation",
        "base_model": "base_model_semantic_results.jsonl",
        "lora_model": "lora_model_semantic_results.jsonl"
    },
    "query_matching": {
        "base_dir": RESULTS_DIR / "4_query_matching",
        "base_model": "base_model_query_matching_results.jsonl",
        "lora_model": "lora_model_query_matching_results.jsonl"
    },
    "final_metrics": {
        "base_dir": RESULTS_DIR / "5_final_metrics",
        "metrics_json": "evaluation_metrics.json",
        "summary_csv": "evaluation_summary.csv"
    }
}

# Prompt file paths
PROMPT_FILES = {
    "text2sql": EVALUATION_DIR / "prompts_new" / "text2sql_prompt.txt",
    "semantic_equivalence": EVALUATION_DIR / "prompts_new" / "semantic_equivalence_eval_prompt.txt",
    "query_matching": EVALUATION_DIR / "prompts_new" / "query_matching_eval_prompt.txt"
}

# Evaluation models configuration
EVALUATION_MODELS = {
    "semantic_equivalence": {
        "api_url": "http://localhost:8000/v1",
        "api_key": "token-abc123",
        "model_name": "Qwen3-30B-A3B",
        "timeout": 60
    },
    "query_matching": {
        "api_url": "http://localhost:8000/v1",
        "api_key": "token-abc123",
        "model_name": "Qwen3-30B-A3B",
        "timeout": 60
    }
}

# Concurrency settings
DEFAULT_MAX_WORKERS = 10
BATCH_SIZE = 32
REQUEST_TIMEOUT = 60

# Evaluation criteria
EVALUATION_CRITERIA = {
    "execution_validity": {
        "weight": 1.0,
        "description": "SQL statement can execute successfully in database"
    },
    "semantic_equivalence": {
        "weight": 1.0,
        "description": "Generated SQL produces same results as gold SQL"
    },
    "query_matching": {
        "weight": 1.0,
        "description": "Generated SQL matches user query requirements"
    }
}

# Final evaluation rules
FINAL_EVALUATION_RULES = {
    "success_condition": "semantic_equivalence OR query_matching",
    "description": "A query is considered correct if it is semantically equivalent to gold SQL OR matches the user query requirements"
}

def get_results_path(step: str, model_type: str = "base_model") -> Path:
    """
    Get results file path for a specific evaluation step and model type.

    Args:
        step: Evaluation step name (e.g., "sql_generation", "execution_validation")
        model_type: Model type ("base_model" or "lora_model")

    Returns:
        Path object for the results file
    """
    step_config = RESULTS_CONFIG.get(step)
    if not step_config:
        raise ValueError(f"Unknown evaluation step: {step}")

    filename = step_config.get(model_type)
    if not filename:
        raise ValueError(f"Unknown model type: {model_type} for step: {step}")

    return step_config["base_dir"] / filename

def ensure_results_directories():
    """Create all necessary results directories"""
    for step_config in RESULTS_CONFIG.values():
        base_dir = step_config["base_dir"]
        base_dir.mkdir(parents=True, exist_ok=True)