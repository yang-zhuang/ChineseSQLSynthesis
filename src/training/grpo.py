# Copyright 2020-2025 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# /// script
# dependencies = [
#     "trl",
#     "peft",
#     "trackio",
#     "kernels",
# ]
# ///

import argparse
import importlib
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

from accelerate import logging
from datasets import load_dataset

from trl import (
    DatasetMixtureConfig,
    GRPOConfig,
    GRPOTrainer,
    ModelConfig,
    ScriptArguments,
    TrlParser,
    get_dataset,
    get_peft_config,
)
from trl.rewards import accuracy_reward, get_soft_overlong_punishment, think_format_reward


logger = logging.get_logger(__name__)

# Enable logging in a Hugging Face Space
os.environ.setdefault("TRACKIO_SPACE_ID", "trl-trackio")


reward_funcs_registry = {
    "accuracy_reward": accuracy_reward,
    "think_format_reward": think_format_reward,
    "get_soft_overlong_punishment": get_soft_overlong_punishment(max_completion_len=1280, soft_punish_cache=256),
}


def load_dataset_from_path_or_hub(dataset_name, dataset_config=None):
    """
    根据给定的数据集名称或路径加载数据集。
    如果是本地路径，则从本地JSONL文件加载数据集；
    否则是从Hugging Face Hub加载数据集。

    参数:
        dataset_name (str): 数据集名称或本地文件路径。
        dataset_config (str, optional): 数据集配置名称（如果适用）。

    返回:
        DatasetDict: 加载的数据集。
    """
    if os.path.exists(dataset_name):
        # 从本地 JSONL 文件加载数据集
        dataset = load_dataset("json", data_files=dataset_name)
    else:
        # 从 Hugging Face Hub 加载数据集
        dataset_kwargs = {"name": dataset_config} if dataset_config else {}
        dataset = load_dataset(
            dataset_name,
            **dataset_kwargs
        )
    return dataset


@dataclass
class GRPOScriptArguments(ScriptArguments):
    """
    Script arguments for the GRPO training script.

    Args:
        reward_model_name_or_path (`str`, *optional*):
            Reward model id of a pretrained model hosted inside a model repo on huggingface.co or local path to a
            directory containing model weights saved using [`~transformers.PreTrainedModel.save_pretrained`].
        reward_funcs (`list[str]`, *optional*):
            Reward functions to use. Supported values are:

                - `"accuracy_reward"`
                - `"think_format_reward"`
                - `"get_soft_overlong_punishment"` (used value are `max_completion_len=1280`, `soft_punish_cache=256`)
                - any dotted import path " (e.g., `'my_lib.rewards.custom_reward'`).
    """

    reward_model_name_or_path: Optional[str] = field(
        default=None,
        metadata={
            "help": "Reward model id of a pretrained model hosted inside a model repo on huggingface.co or "
            "local path to a directory containing model weights saved using `PreTrainedModel.save_pretrained`."
        },
    )
    reward_funcs: Optional[list[str]] = field(
        default=None,
        metadata={
            "help": "Reward functions to use. Supported values are: `accuracy_reward`, `think_format_reward`, "
            "`get_soft_overlong_punishment` (used value are `max_completion_len=1280`, `soft_punish_cache=256`), or "
            "any dotted import path (e.g., `'my_lib.rewards.custom_reward'`)."
        },
    )


def main(script_args, training_args, model_args, dataset_args):
    # Get the reward models and functions
    reward_funcs = []
    if script_args.reward_model_name_or_path:
        reward_funcs.append(script_args.reward_model_name_or_path)

    if script_args.reward_funcs:
        for func_name in script_args.reward_funcs:
            if func_name in reward_funcs_registry:
                reward_funcs.append(reward_funcs_registry[func_name])
            elif "." in func_name:
                module_path, func_name = func_name.rsplit(".", 1)
                # 确保项目根目录在Python路径中
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                sys.path.insert(0, project_root)  # 总是插入到最前面
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, project_root)  # 总是插入到最前面
                print(f"🔍 尝试导入模块: {module_path} (项目根目录: {project_root})")
                try:
                    module = importlib.import_module(module_path)
                    reward_func = getattr(module, func_name)
                    reward_funcs.append(reward_func)
                    print(f"✅ 成功导入奖励函数: {func_name}")
                except ImportError as e:
                    print(f"❌ 导入失败: {e}")
                    print(f"❌ 当前Python路径: {sys.path[:3]}")  # 显示前3个路径
                    raise
            else:
                raise ValueError(
                    f"Could not load reward function '{func_name}'. Expected one of "
                    f"{list(reward_funcs_registry.keys())} or a valid import path."
                )

    # Load the dataset
    if dataset_args.datasets and script_args.dataset_name:
        logger.warning(
            "Both `datasets` and `dataset_name` are provided. The `datasets` argument will be used to load the "
            "dataset and `dataset_name` will be ignored."
        )
        dataset = get_dataset(dataset_args)
    elif dataset_args.datasets and not script_args.dataset_name:
        dataset = get_dataset(dataset_args)
    elif not dataset_args.datasets and script_args.dataset_name:
        dataset = load_dataset_from_path_or_hub(script_args.dataset_name, script_args.dataset_config)
    else:
        raise ValueError("Either `datasets` or `dataset_name` must be provided.")

    # Initialize the GRPO trainer
    trainer = GRPOTrainer(
        model=model_args.model_name_or_path,
        reward_funcs=reward_funcs,
        args=training_args,
        train_dataset=dataset[script_args.dataset_train_split],
        eval_dataset=dataset[script_args.dataset_test_split] if training_args.eval_strategy != "no" else None,
        peft_config=get_peft_config(model_args),
    )

    # Train the model
    trainer.train()

    # Log training complete
    trainer.accelerator.print("✅ Training completed.")

    # Save and push to Hub
    trainer.save_model(training_args.output_dir)
    trainer.accelerator.print(f"💾 Model saved to {training_args.output_dir}.")

    if training_args.push_to_hub:
        trainer.push_to_hub(dataset_name=script_args.dataset_name)
        trainer.accelerator.print(f"🤗 Model pushed to the Hub in https://huggingface.co/{trainer.hub_model_id}.")


def make_parser(subparsers: Optional[argparse._SubParsersAction] = None):
    dataclass_types = (GRPOScriptArguments, GRPOConfig, ModelConfig, DatasetMixtureConfig)
    if subparsers is not None:
        parser = subparsers.add_parser("grpo", help="Run the GRPO training script", dataclass_types=dataclass_types)
    else:
        parser = TrlParser(dataclass_types)
    return parser


if __name__ == "__main__":
    parser = make_parser()
    # When using the trl cli, this script may be run with additional arguments, corresponding accelerate arguments.
    # To ensure that their parsing does not interfere with the script arguments, parse the arguments with
    # `return_remaining_strings=True`, then ignore the remaining strings.
    script_args, training_args, model_args, dataset_args, _ = parser.parse_args_and_config(
        return_remaining_strings=True
    )
    main(script_args, training_args, model_args, dataset_args)
