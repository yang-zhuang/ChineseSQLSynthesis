"""
ChineseSQLSynthesis - 训练数据处理器 (Training Data Processor)

通用的训练数据后处理模块，将data_synthesis生成的问句-SQL对转换为可用于模型训练的格式。

主要功能：
1. 提示词模板生成
2. SQL结构信息提取
3. 训练数据格式化
4. 数据验证和质量控制

Author: Claude Code Assistant
Version: 1.2.0
Project: ChineseSQLSynthesis
"""

__version__ = "1.2.0"
__author__ = "Claude Code Assistant"

from .prompt_template_generator import PromptTemplateGenerator
from .sql_structure_extractor import SQLStructureExtractor
from .training_formatter import TrainingFormatter
from .data_validator import DataValidator

__all__ = [
    'PromptTemplateGenerator',
    'SQLStructureExtractor',
    'TrainingFormatter',
    'DataValidator'
]