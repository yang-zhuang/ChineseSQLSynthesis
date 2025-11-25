"""
SQL生成运行脚本
用于批量生成Text-to-SQL预测结果
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.evaluation.config_new.evaluation_config import (
    DEFAULT_TEST_DATA_PATH, get_results_path, ensure_results_directories
)
from src.evaluation.config_new.model_config import TEXT2SQL_MODELS
from sql_generator import SQLGenerator


def main():
    parser = argparse.ArgumentParser(description="批量生成Text-to-SQL预测结果")

    parser.add_argument(
        "--data_path",
        type=str,
        default=str(DEFAULT_TEST_DATA_PATH),
        help="输入数据文件路径 (默认: test.jsonl)"
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
    print("SQL生成评估脚本")
    print("=" * 60)
    print(f"输入数据: {args.data_path}")
    print(f"模型类型: {args.model_type}")
    print(f"并发线程数: {args.max_workers}")
    print(f"调试模式: {'是' if args.debug else '否'}")
    if args.debug:
        print(f"调试样本数: {args.debug_samples}")
    print("=" * 60)

    try:
        # 确保结果目录存在
        ensure_results_directories()

        # 加载数据
        data_path = Path(args.data_path)
        if not data_path.exists():
            print(f"错误: 数据文件不存在 - {data_path}")
            return 1

        print("正在加载数据...")
        data_list = SQLGenerator.load_data(data_path)

        # 调试模式处理
        if args.debug:
            print(f"调试模式: 只处理前 {args.debug_samples} 个样本")
            data_list = data_list[:args.debug_samples]

        print(f"成功加载 {len(data_list)} 个数据样本")

        # 设置输出路径
        if args.output_path:
            output_path = Path(args.output_path)
        else:
            output_path = get_results_path("sql_generation", args.model_type)

        print(f"输出路径: {output_path}")

        # 初始化SQL生成器
        print(f"正在初始化 {args.model_type} SQL生成器...")
        generator = SQLGenerator(model_type=args.model_type, max_workers=args.max_workers)

        # 批量生成SQL
        print("开始批量生成SQL...")
        stats = generator.generate_batch_sql(data_list, output_path)

        # 输出统计信息
        print("\\n" + "=" * 60)
        print("生成结果统计")
        print("=" * 60)
        print(f"总样本数: {stats['total_items']}")
        print(f"成功生成: {stats['successful_generations']}")
        print(f"失败生成: {stats['failed_generations']}")
        print(f"成功率: {stats['success_rate']:.2%}")
        print(f"结果文件: {stats['results_file']}")
        print("=" * 60)

        return 0 if stats['success_rate'] > 0 else 1

    except Exception as e:
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())