"""
评估指标汇总运行脚本
收集所有评估步骤的结果，计算最终评估指标
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.evaluation.config_new.evaluation_config import (
    RESULTS_CONFIG, get_results_path, ensure_results_directories
)
from metrics_aggregator import MetricsAggregator


def main():
    parser = argparse.ArgumentParser(description="汇总评估指标，生成最终评估报告")

    parser.add_argument(
        "--model_type",
        type=str,
        choices=["base_model", "lora_model"],
        default="base_model",
        help="模型类型选择 (默认: all - 处理所有模型类型)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="输出目录路径 (默认使用配置中的路径)"
    )
    parser.add_argument(
        "--generate_report",
        action="store_true",
        help="生成详细的评估报告"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("评估指标汇总脚本")
    print("=" * 60)
    print(f"模型类型: {args.model_type}")
    print(f"生成详细报告: {'是' if args.generate_report else '否'}")
    print("=" * 60)

    try:
        # 确保结果目录存在
        ensure_results_directories()

        # 初始化指标汇总器
        aggregator = MetricsAggregator()

        # 确定要处理的模型类型
        if args.model_type == "all":
            model_types = ["base_model", "lora_model"]
        else:
            model_types = [args.model_type]

        # 设置输出目录
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = RESULTS_CONFIG["final_metrics"]["base_dir"]

        output_dir.mkdir(parents=True, exist_ok=True)

        # 处理每种模型类型
        all_model_metrics = {}

        for model_type in model_types:
            print(f"\n正在处理 {model_type}...")

            # 加载所有评估结果
            print("  1. 加载评估结果...")
            all_results = aggregator.load_all_results(model_type)

            if not any(all_results.values()):
                print(f"  警告: {model_type} 没有找到任何评估结果，跳过")
                continue

            # 合并结果
            print("  2. 合并评估结果...")
            merged_results = aggregator.merge_results(all_results, model_type)

            # 计算指标
            print("  3. 计算评估指标...")
            metrics = aggregator.calculate_metrics(merged_results)
            metrics["model_type"] = model_type
            all_model_metrics[model_type] = metrics

            # 保存详细结果
            if args.generate_report:
                detailed_path = output_dir / f"{model_type}_detailed_results.csv"
                print(f"  4. 保存详细结果到 {detailed_path}...")
                aggregator.save_detailed_results(merged_results, detailed_path)

        # 保存最终指标
        print("\n保存最终指标...")
        metrics_path = output_dir / RESULTS_CONFIG["final_metrics"]["metrics_json"]

        if len(model_types) == 1:
            # 单个模型类型
            final_metrics = list(all_model_metrics.values())[0]
        else:
            # 多个模型类型对比
            final_metrics = {
                "evaluation_comparison": all_model_metrics,
                "evaluation_timestamp": all_model_metrics[model_types[0]]["evaluation_timestamp"],
                "total_models_evaluated": len(all_model_metrics)
            }

        aggregator.save_metrics(final_metrics, metrics_path)

        # 生成并打印摘要报告
        print("\n" + "=" * 60)
        print("评估完成 - 摘要报告")
        print("=" * 60)

        for model_type, metrics in all_model_metrics.items():
            print(f"\n📊 {model_type.upper()} 模型评估结果:")
            print(f"  - 总样本数: {metrics['total_samples']}")
            print(f"  - SQL可执行率: {metrics['execution_validity']['validity_rate']:.2%}")
            print(f"  - 语义等价率: {metrics['semantic_equivalence']['equivalence_rate']:.2%}")

        if len(model_types) > 1:
            print("\n🔄 模型对比:")
            base_acc = all_model_metrics["base_model"]["overall_correctness"]["correctness_rate"]
            lora_acc = all_model_metrics["lora_model"]["overall_correctness"]["correctness_rate"]
            improvement = lora_acc - base_acc
            print(f"  - LoRA vs Base 准确率提升: {improvement:+.2%}")
            print(f"  - Base模型准确率: {base_acc:.2%}")
            print(f"  - LoRA模型准确率: {lora_acc:.2%}")

        print(f"\n📁 结果保存位置:")
        print(f"  - 指标文件: {metrics_path}")
        if args.generate_report:
            summary_path = output_dir / f"evaluation_summary.txt"
            with open(summary_path, 'w', encoding='utf-8') as f:
                for model_type, metrics in all_model_metrics.items():
                    report = aggregator.generate_summary_report(metrics)
                    f.write(f"{model_type.upper()} 模型\n")
                    f.write(report + "\n\n")
            print(f"  - 摘要报告: {summary_path}")

        print("=" * 60)
        print("评估指标汇总完成！")
        return 0

    except Exception as e:
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())