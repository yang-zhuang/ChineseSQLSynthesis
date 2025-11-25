"""
SQL语义等价性评估运行脚本
用于批量评估生成的SQL与gold SQL是否语义等价
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.evaluation.config_new.evaluation_config import (
    get_results_path, ensure_results_directories
)
from semantic_evaluator import SemanticEvaluator


def main():
    parser = argparse.ArgumentParser(description="批量评估SQL语义等价性")

    parser.add_argument(
        "--input_path",
        type=str,
        default="../../../evaluation_results/2_execution_validation/base_model_execution_results.jsonl",
        help="SQL执行验证结果文件路径"
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
        default=5,
        help="并发工作线程数 (默认: 5)"
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
    print("SQL语义等价性评估脚本")
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

        # 加载SQL执行验证结果
        input_path = Path(args.input_path)
        if not input_path.exists():
            print(f"错误: 输入文件不存在 - {input_path}")
            return 1

        print("正在加载SQL执行验证结果...")
        data_list = SemanticEvaluator.load_execution_results(input_path)

        # 调试模式处理
        if args.debug:
            print(f"调试模式: 只处理前 {args.debug_samples} 个样本")
            data_list = data_list[:args.debug_samples]

        print(f"成功加载 {len(data_list)} 个SQL执行验证结果")

        # 设置输出路径
        if args.output_path:
            output_path = Path(args.output_path)
        else:
            output_path = get_results_path("semantic_evaluation", args.model_type)

        print(f"输出路径: {output_path}")

        # 初始化语义评估器
        print("正在初始化语义等价性评估器...")
        evaluator = SemanticEvaluator(max_workers=args.max_workers)

        # 批量评估语义等价性
        print("开始批量评估语义等价性...")
        stats = evaluator.evaluate_batch_semantic(data_list, output_path)

        # 输出统计信息
        print("\\n" + "=" * 60)
        print("语义等价性评估结果统计")
        print("=" * 60)
        print(f"总样本数: {stats['total_items']}")
        print(f"语义等价: {stats['semantically_equivalent']}")
        print(f"语义不等价: {stats['semantically_nonequivalent']}")
        print(f"评估错误: {stats['evaluation_errors']}")
        print(f"等价率: {stats['equivalence_rate']:.2%}")
        print(f"评估成功率: {stats['success_rate']:.2%}")
        print(f"使用模型: {stats['model_used']}")
        print(f"结果文件: {stats['results_file']}")
        print("=" * 60)

        return 0 if stats['success_rate'] > 0 else 1

    except Exception as e:
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())