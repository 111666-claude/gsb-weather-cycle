"""天气循环：随机转移、持续时间与属性修正。

口径（见 README）：

- 转移权重先按行归一化到和为 1，再按累计分布采样；权重不足或超过 1 都按
  比例缩放，保证每个正权重分支都有机会被选中。
- 速度修正只作用于移动速度：雨 ×0.8、雪 ×0.7、其它 ×1.0，不影响转移与碰撞。
- 每种天气的持续时长在配置的 [min, max] 范围内随机整数。
- 转移流与持续时长流各自独立、由同一颗种子确定性派生：同一种子重放结果
  完全一致。默认表导入时归一化一次，常驻内存 O(状态数)。
"""

import random

# 原始配置表：保持配置里的原始权重，采样前统一归一化（sunny/rain 行不足 1，
# 即题目中 --sample table 暴露出来的问题来源）。
TABLE = {
    "sunny": [("sunny", 0.6), ("rain", 0.3)],
    "rain": [("rain", 0.7), ("sunny", 0.2)],
    "snow": [("snow", 1.0)],
}

# 每种天气的持续时长范围（秒，闭区间）。
DURATION_RANGES = {
    "sunny": (30, 90),
    "rain": (40, 120),
    "snow": (50, 150),
}

_DURATION_SEED_SALT = 0x9E3779B97F4A7C15


def normalize_rows(table):
    """把每行权重按比例缩放到和为 1。

    返回 {state: [(name, normalized_weight), ...]}；零权重行原样保留
    （调用方应保证配置里每行权重和为正）。
    """
    normalized = {}
    for state, branches in table.items():
        total = sum(weight for _, weight in branches)
        if total > 0:
            normalized[state] = [(name, weight / total) for name, weight in branches]
        else:
            normalized[state] = list(branches)
    return normalized


# 默认配置表在导入时归一化一次；常驻内存 O(状态数)。
_DEFAULT_ROWS = normalize_rows(TABLE)


def _normalized(table):
    """取归一化行：默认表用导入时预算好的结果；自定义表按需归一化、不缓存。"""
    if table is TABLE:
        return _DEFAULT_ROWS
    return normalize_rows(table)


def pick(rng, state, table=None):
    """按归一化后的累计分布挑下一个天气。

    rng 是无参可调用对象，返回 [0, 1) 的均匀随机数（random.Random.random）。
    table 为 None 时使用默认配置表，也可传入自定义权重表做对照验证。
    """
    rows = _normalized(TABLE if table is None else table)
    roll = rng()
    cumulative = 0.0
    for name, weight in rows[state]:
        cumulative += weight
        if roll < cumulative:
            return name
    return rows[state][-1][0]


def weight_sum(state):
    """诊断用：归一化后某一行的权重和（口径恒为 1）。"""
    return sum(weight for _, weight in _normalized(TABLE)[state])


def speed_modifier(weather):
    """速度修正系数：雨 ×0.8（减速）、雪 ×0.7，其它天气 ×1.0。"""
    if weather == "rain":
        return 0.8
    if weather == "snow":
        return 0.7
    return 1.0


def sample_duration(rng, weather, ranges=None):
    """在配置的 [min, max] 闭区间内随机取一个持续时长。"""
    bounds = DURATION_RANGES if ranges is None else ranges
    minimum, maximum = bounds[weather]
    return rng.randint(minimum, maximum)


def _duration_seed(seed):
    """从转移种子确定性派生出独立的持续时长流种子。"""
    return (seed ^ _DURATION_SEED_SALT) & 0xFFFFFFFFFFFFFFFF


def weather_sequence(seed, start, steps, table=None):
    """参考口径的天气序列：独立 Random，逐次 uniform(0,1) 后走累计分布。

    只消费转移随机流，持续时长另走独立流，因此同一种子在任何调用方式下
    给出同一串天气。
    """
    rows = _normalized(TABLE if table is None else table)
    rng = random.Random(seed)
    state = start
    sequence = []
    for _ in range(steps):
        roll = rng.random()
        cumulative = 0.0
        for name, weight in rows[state]:
            cumulative += weight
            if roll < cumulative:
                state = name
                break
        else:
            state = rows[state][-1][0]
        sequence.append(state)
    return sequence


class WeatherCycle:
    """确定性天气循环：天气段 = 天气 + 随机持续时长。

    转移流与持续时长流使用同一颗种子派生出的两条独立随机流，因此
    同一种子重复回放（同一批转移）结果完全相同；归一化表全实例共享
    一份，单个实例只持有 O(1) 状态。
    """

    def __init__(self, seed, start="sunny", table=None, ranges=None):
        self.seed = seed
        self.table = TABLE if table is None else table
        self.ranges = DURATION_RANGES if ranges is None else ranges
        self._transition_rng = random.Random(seed)
        self._duration_rng = random.Random(_duration_seed(seed))
        self.state = start
        self.remaining = 0

    def next_weather(self):
        """走一次归一化累计分布转移，返回新天气（不触碰持续时长流）。"""
        self.state = pick(self._transition_rng.random, self.state, self.table)
        return self.state

    def next_spell(self):
        """推进到下一天气段，返回 (天气, 持续时长)。"""
        self.next_weather()
        duration = sample_duration(self._duration_rng, self.state, self.ranges)
        self.remaining = duration
        return self.state, duration

    def replay(self, spells):
        """从头按同一颗种子回放若干天气段；重复调用结果必须逐段相同。"""
        self._transition_rng = random.Random(self.seed)
        self._duration_rng = random.Random(_duration_seed(self.seed))
        result = []
        for _ in range(spells):
            result.append(self.next_spell())
        return result
