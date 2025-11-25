"""
SQL执行验证运行脚本
用于批量验证生成的SQL是否能成功执行
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.evaluation.config_new.evaluation_config import (
    get_results_path, ensure_results_directories
)
from src.evaluation.config_new.model_config import TEXT2SQL_MODELS
from execution_validator import SQLExecutionValidator


def main():
    parser = argparse.ArgumentParser(description="批量验证SQL执行结果")

    parser.add_argument(
        "--input_path",
        type=str,
        default='../../../evaluation_results/1_sql_generation/base_model_predictions.jsonl',
        help="SQL生成结果文件路径"
    )
    parser.add_argument(
        "--model_type",
        type=str,
        choices=["base_model", "lora_model"],
        default="base_model",
        help="模型类型选择 (默认: base_model)"
    )
    parser.add_argument(
        "--max_workers",
        type=int,
        default=10,
        help="并发工作线程数 (默认: 10)"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default=None,
        help="输出文件路径 (默认使用配置中的路径)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="调试模式，只处理少量样本"
    )
    parser.add_argument(
        "--debug_samples",
        type=int,
        default=10,
        help="调试模式下的样本数量 (默认: 10)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("SQL执行验证脚本")
    print("=" * 60)
    print(f"输入数据: {args.input_path}")
    print(f"模型类型: {args.model_type}")
    print(f"并发线程数: {args.max_workers}")
    print(f"调试模式: {'是' if args.debug else '否'}")
    if args.debug:
        print(f"调试样本数: {args.debug_samples}")
    print("=" * 60)

    try:
        # 确保结果目录存在
        ensure_results_directories()

        # 加载SQL生成结果
        input_path = Path(args.input_path)
        if not input_path.exists():
            print(f"错误: 输入文件不存在 - {input_path}")
            return 1

        print("正在加载SQL生成结果...")
        data_list = SQLExecutionValidator.load_generation_results(input_path)

        # 调试模式处理
        if args.debug:
            print(f"调试模式: 只处理前 {args.debug_samples} 个样本")
            data_list = data_list[:args.debug_samples]

        print(f"成功加载 {len(data_list)} 个SQL生成结果")

        # 设置输出路径
        if args.output_path:
            output_path = Path(args.output_path)
        else:
            output_path = get_results_path("execution_validation", args.model_type)

        print(f"输出路径: {output_path}")

        # 初始化SQL执行验证器
        print("正在初始化SQL执行验证器...")
        validator = SQLExecutionValidator(max_workers=args.max_workers)

        # 批量验证SQL执行
        print("开始批量验证SQL执行...")
        stats = validator.validate_batch_sql(data_list, output_path)

        # 输出统计信息
        print("\\n" + "=" * 60)
        print("验证结果统计")
        print("=" * 60)
        print(f"总样本数: {stats['total_items']}")
        print(f"成功执行: {stats['valid_executions']}")
        print(f"执行失败: {stats['invalid_executions']}")
        print(f"超时次数: {stats['timeout_occurrences']}")
        print(f"执行成功率: {stats['execution_rate']:.2%}")
        print(f"平均执行时间: {stats['average_execution_time']:.3f}s")
        print(f"总执行时间: {stats['total_execution_time']:.3f}s")
        print(f"结果文件: {stats['results_file']}")
        print("=" * 60)

        return 0 if stats['execution_rate'] > 0 else 1

    except Exception as e:
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())