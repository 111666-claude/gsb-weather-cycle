"""天气循环：随机转移、持续时间与属性修正，只用标准库。"""

TABLE = {
    "sunny": [("sunny", 0.6), ("rain", 0.3)],
    "rain": [("rain", 0.7), ("sunny", 0.2)],
    "snow": [("snow", 1.0)],
}

DURATIONS = {
    "sunny": (4.0, 10.0),
    "rain": (2.0, 6.0),
    "snow": (3.0, 8.0),
}

_MODIFIERS = {"rain": 0.8, "snow": 0.7}


def normalize_row(row):
    """把一行权重归一化到和为 1，不足按比例补齐。"""
    total = sum(weight for _, weight in row)
    if total <= 0:
        raise ValueError("权重和必须为正")
    names = [name for name, _ in row]
    weights = [weight / total for _, weight in row]
    weights[-1] = 1.0 - sum(weights[:-1])
    return list(zip(names, weights))


def _cumulative(row):
    acc = 0.0
    out = []
    for name, weight in row:
        acc += weight
        out.append((name, acc))
    return out


def _normalized_table(table):
    return {state: _cumulative(normalize_row(row)) for state, row in table.items()}


_NORMALIZED = _normalized_table(TABLE)


def pick(rng, state, table=None):
    """按归一化后的累计分布挑下一个天气，rng 是返回 [0, 1) 的 callable。"""
    row = _NORMALIZED[state] if table is None else _normalized_table(table)[state]
    roll = rng()
    for name, cum in row:
        if roll < cum:
            return name
    return row[-1][0]


def weight_sum(state):
    """诊断用：某一行归一化后的权重和（恒为 1）。"""
    return sum(weight for _, weight in normalize_row(TABLE[state]))


def speed_modifier(weather):
    """速度修正：雨天 ×0.8、雪天 ×0.7，其它 ×1.0。只影响速度，不改碰撞判定。"""
    return _MODIFIERS.get(weather, 1.0)


def duration(rng, weather):
    """持续时长：在配置范围 [最小, 最大] 内随机，rng 是返回 [0, 1) 的 callable。"""
    low, high = DURATIONS[weather]
    return low + rng() * (high - low)


def simulate(seed, steps, start="sunny"):
    """同一种子给出同一串天气，重复回放结果相同。"""
    import random

    rng = random.Random(seed)
    weather = start
    sequence = []
    for _ in range(steps):
        sequence.append(weather)
        weather = pick(rng.random, weather)
    return sequence
