"""天气循环：随机转移、持续时间与属性修正。

缺陷：转移权重没有归一化（累计概率不足 1 时恒选最后一项）、雨天速度修正符号反了。
"""

TABLE = {
    "sunny": [("sunny", 0.6), ("rain", 0.3)],
    "rain": [("rain", 0.7), ("sunny", 0.2)],
    "snow": [("snow", 1.0)],
}


def pick(rng, state):
    """按权重挑下一个天气。缺陷：不归一化，roll 落在尾部时直接返回最后一项。"""
    roll = rng()
    total = 0.0
    for name, weight in TABLE[state]:
        total += weight
        if roll < total:
            return name
    return TABLE[state][-1][0]


def weight_sum(state):
    """诊断用：某一行的权重和。"""
    return sum(weight for _, weight in TABLE[state])


def speed_modifier(weather):
    """速度修正。缺陷：雨天给了加速，口径是减速。"""
    if weather == "rain":
        return 1.2
    return 1.0
