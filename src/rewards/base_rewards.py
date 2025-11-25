from collections.abc import Callable


def get_soft_overlong_punishment(max_completion_len: int, soft_punish_cache: int) -> Callable:
    """
    软性超长惩罚：对过长完成文本进行软性惩罚的函数生成器

    分数设计：
    - 范围：-1.0 到 0.0
    - 基于完成文本长度与最大长度的关系进行惩罚
    - 计算公式（参考DAPO论文Eq. (13)）：
        * 长度 ≤ (最大长度 - 缓存长度)：0.0（无惩罚）
        * (最大长度 - 缓存长度) < 长度 ≤ 最大长度：-(当前长度 - (最大长度 - 缓存长度)) / 缓存长度
        * 长度 > 最大长度：-1.0（最大惩罚）

    参数：
        max_completion_len (int): 完成文本的最大允许长度 L_max
        soft_punish_cache (int): 软惩罚缓存长度 L_cache，设置为0时不应用最小长度

    返回：
        Callable: 接受完成文本ID列表并返回惩罚分数列表的函数

    示例：
        >>> soft_overlong_punishment = get_soft_overlong_punishment(
        ...     max_completion_len=100, 
        ...     soft_punish_cache=20
        ... )
        >>> completion_ids = [[1] * 90]  # 模拟90个token的完成文本
        >>> rewards = soft_overlong_punishment(completion_ids)
        >>> print(rewards)  # [-0.5]
        # 解释：90在80-100之间，惩罚 = -(90-80)/20 = -10/20 = -0.5

    更多示例：
        - 长度=70 (≤80): 惩罚=0.0
        - 长度=85 (80-100之间): 惩罚=-(85-80)/20 = -0.25
        - 长度=95 (80-100之间): 惩罚=-(95-80)/20 = -0.75
        - 长度=110 (>100): 惩罚=-1.0
    """

    def soft_overlong_punishment_reward(completion_ids: list[list[int]], **kwargs) -> list[float]:
        """软性超长惩罚函数实现"""
        rewards = []
        for ids in completion_ids:
            completion_length = len(ids)
            if completion_length <= max_completion_len - soft_punish_cache:
                rewards.append(0.0)
            elif max_completion_len - soft_punish_cache < completion_length <= max_completion_len:
                rewards.append((max_completion_len - soft_punish_cache - completion_length) / soft_punish_cache)
            else:
                rewards.append(-1.0)
        return rewards

    return soft_overlong_punishment_reward


# 默认版本（与TRL相同）
def get_soft_overlong_punishment_default(**kwargs) -> Callable:
    """默认版本：max_completion_len=1280, soft_punish_cache=256"""
    return get_soft_overlong_punishment(max_completion_len=1280, soft_punish_cache=256)(**kwargs)


# 中等长度版本
def get_soft_overlong_punishment_medium(**kwargs) -> Callable:
    """中等版本：max_completion_len=1024, soft_punish_cache=128"""
    return get_soft_overlong_punishment(max_completion_len=1024, soft_punish_cache=128)(**kwargs)


# 短文本版本
def get_soft_overlong_punishment_short(**kwargs) -> Callable:
    """短文本版本：max_completion_len=512, soft_punish_cache=64"""
    return get_soft_overlong_punishment(max_completion_len=512, soft_punish_cache=64)(**kwargs)


# 长文本版本
def get_soft_overlong_punishment_long(**kwargs) -> Callable:
    """长文本版本：max_completion_len=2048, soft_punish_cache=512"""
    return get_soft_overlong_punishment(max_completion_len=2048, soft_punish_cache=512)(**kwargs)


# 超长文本版本
def get_soft_overlong_punishment_xlong(**kwargs) -> Callable:
    """超长文本版本：max_completion_len=4096, soft_punish_cache=1024"""
    return get_soft_overlong_punishment(max_completion_len=4096, soft_punish_cache=1024)(**kwargs)