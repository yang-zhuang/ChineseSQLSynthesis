import re
import json_repair


def think_tag_penalty(completions: list[list[dict[str, str]]], **kwargs) -> list[float]:
    """
    思考标签惩罚：检查生成内容中是否包含</think>标签

    分数设计：
    - 包含</think>标签：0.0（无惩罚）
    - 不包含</think>标签：-1.0（有惩罚）

    示例：
    - 内容："<think>...</think>..." → 惩罚：0.0
    - 内容："直接回答" → 惩罚：-1.0
    """
    if isinstance(completions[0], str):
        completion_contents = [completion for completion in completions]
    else:
        completion_contents = [completion[0]["content"] for completion in completions]

    penalties = []
    for content in completion_contents:
        # 检查是否包含</think>标签
        if "</think>" in content:
            penalties.append(0.0)  # 包含标签，无惩罚
        else:
            penalties.append(-1.0)  # 不包含标签，有惩罚

    return penalties


def valid_sql_markdown_reward(completions: list[list[dict[str, str]]], **kwargs) -> list[float]:
    """
    有效SQL标记奖励：检查是否能从内容中提取出有效的SQL代码块

    分数设计：
    - 能找到有效的```sql...```标记并提取出SQL代码：1.0（有奖励）
    - 不能找到有效标记或标记内无内容：-1.0（无奖励）

    示例：
    - 内容："```sql\nSELECT * FROM users\n```" → 奖励：1.0
    - 内容："```sql\n```" → 奖励：-1.0（空代码块）
    - 内容："没有SQL代码" → 奖励：-1.0
    - 内容："```sql SELECT * FROM users```" → 奖励：-1.0（缺少换行）
    - 内容："```SQL\nSELECT * FROM users\n```" → 奖励：1.0（不区分大小写）
    """
    if isinstance(completions[0], str):
        completion_contents = [completion for completion in completions]
    else:
        completion_contents = [completion[0]["content"] for completion in completions]

    rewards = []
    for content in completion_contents:
        # 如果存在</think>标签，提取之后的内容
        if '</think>' in content:
            think_match = re.search("</think>(.*?)$", content, re.DOTALL)
            if think_match:
                content = think_match.group(1).strip()

        # 使用正则表达式查找```sql...```代码块
        sql_block_pattern = r"```sql\s*(.*?)```"
        matches = re.findall(sql_block_pattern, content, re.DOTALL | re.IGNORECASE)

        # 分配奖励
        if matches:
            rewards.append(1.0)  # 找到有效的SQL代码块，有奖励
        else:
            rewards.append(-1.0)  # 未找到有效的SQL代码块，无奖励

    return rewards
