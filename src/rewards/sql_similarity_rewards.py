import re
from typing import Optional


def remove_sql_comments(sql: str) -> str:
    """
    移除SQL语句中的注释和可能的Markdown代码块标记
    """
    if not sql.strip():
        return ""

    if "</think>" in sql:
        try:
            sql = re.search("</think>(.*?)$", sql, re.DOTALL).group(1).strip()
        except Exception as e:
            pass

    # 移除 Markdown 代码块标记
    sql = re.sub(r'```(?:sql)?', '', sql, flags=re.IGNORECASE)
    sql=sql.strip()
    # 移除单行注释 (--)
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    # 移除多行注释 (/* */)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    # 清理多余的空格
    sql = re.sub(r'\s+', ' ', sql).strip()

    if sql.endswith(';') or sql.endswith(';'):
        sql = sql[:-1]
    return sql


def sql_word_reward(completions: list[list[dict[str, str]]], ground_truth, **kwargs) -> list[Optional[float]]:
    """
    SQL单词奖励函数：计算生成SQL中的单词有多少比例出现在gold SQL中（精确率）

    分数设计：
    - 范围：0.0 到 1.0
    - 计算公式：生成SQL中出现在gold中的单词数量 / 生成SQL总单词数
    """

    def _parse_completion_content(completion):
        """
        解析模型生成的SQL内容
        这里假设completion是一个列表，包含字典，字典中有"text"字段包含SQL
        """
        if not completion:
            return ''
        # 取第一个completion的text内容
        return completion[0].get("content", "") if completion else ""

    rewards = []
    for completion, truth_sql in zip(completions, ground_truth):
        # 解析生成内容 - 获取SQL字符串
        generated_sql = _parse_completion_content(completion)
        if generated_sql is None:
            rewards.append(0.0)
            continue

        # 处理生成的SQL：移除注释，拆分并转为小写
        clean_generated_sql = remove_sql_comments(generated_sql)

        # 将 生成的SQL 拆分成单词（仅用于计算总数）
        gen_tokens = [w.strip().lower() for w in clean_generated_sql.split() if w.strip()]

        if not gen_tokens:
            # 生成为空：如果gold也为空，则满分；否则0分
            rewards.append(1.0 if not truth_sql else 0.0)
            continue

        # 计算生成词中有多少在gold中
        matched = sum(1 for word in gen_tokens if word.lower() in truth_sql.lower())
        precision = matched / len(gen_tokens)

        rewards.append(float(precision))

    return rewards


def sql_word_penalty(completions: list[list[dict[str, str]]], ground_truth, **kwargs) -> list[Optional[float]]:
    """
    SQL单词惩罚函数：基于遗漏率的惩罚

    分数设计：
    - 范围：-1.0 到 0.0
    - 计算公式：-1 * (gold SQL中未出现在生成SQL中的单词数量 / gold SQL总单词数)
    """

    def _parse_completion_content(completion):
        """解析模型生成的SQL内容"""
        if not completion:
            return None
        return completion[0].get("content", "") if completion else ""

    penalties = []
    for completion, truth_sql in zip(completions, ground_truth):
        # 解析生成内容
        generated_sql = _parse_completion_content(completion)
        if not generated_sql:
            # 完全没有生成：严重惩罚
            penalties.append(-1.0)
            continue

        # 清理SQL并获取单词列表
        clean_truth_sql = remove_sql_comments(truth_sql)
        gold_tokens = [w.strip().lower() for w in clean_truth_sql.split() if w.strip()]

        # 特殊情况处理
        if not gold_tokens:
            penalties.append(0.0)
            continue

        # 计算gold中有多少单词未出现在生成SQL中
        missing_count  = sum(1 for word in gold_tokens if word.lower() not in generated_sql.lower())
        missing_ratio = missing_count  / len(gold_tokens)

        penalty_score = -min(missing_ratio, 1.0)
        penalties.append(float(penalty_score))

    return penalties