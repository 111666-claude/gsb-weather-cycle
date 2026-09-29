import random
import time
import unittest

from weathercycle.cycle import (
    DURATIONS,
    TABLE,
    duration,
    normalize_row,
    pick,
    simulate,
    speed_modifier,
    weight_sum,
)


def reference_sequence(table, seed, steps, start):
    """参考实现：归一化 + 累计分布采样。"""
    normalized = {}
    for state, row in table.items():
        total = sum(w for _, w in row)
        cumulative = []
        acc = 0.0
        for name, w in row:
            acc += w / total
            cumulative.append((name, acc))
        normalized[state] = cumulative
    rng = random.Random(seed)
    weather = start
    sequence = []
    for _ in range(steps):
        sequence.append(weather)
        roll = rng.random()
        nxt = normalized[weather][-1][0]
        for name, cum in normalized[weather]:
            if roll < cum:
                nxt = name
                break
        weather = nxt
    return sequence


def implementation_sequence(table, seed, steps, start):
    rng = random.Random(seed)
    weather = start
    sequence = []
    for _ in range(steps):
        sequence.append(weather)
        weather = pick(rng.random, weather, table=table)
    return sequence


class NormalizeTest(unittest.TestCase):
    def test_every_row_sums_to_one(self):
        for state in TABLE:
            self.assertEqual(weight_sum(state), 1.0)

    def test_normalize_row_scales_proportionally(self):
        row = normalize_row([("a", 2.0), ("b", 1.0), ("c", 1.0)])
        self.assertEqual([name for name, _ in row], ["a", "b", "c"])
        self.assertAlmostEqual(row[0][1], 0.5)
        self.assertAlmostEqual(row[1][1], 0.25)
        self.assertEqual(sum(w for _, w in row), 1.0)

    def test_normalize_row_rejects_nonpositive_total(self):
        with self.assertRaises(ValueError):
            normalize_row([("a", 0.0)])

    def test_tail_roll_no_longer_stuck_on_last(self):
        # sunny 行原始权重和 0.9：roll=0.95 归一化后落在 rain 区间外应重映射，而不是恒选末项
        self.assertEqual(pick(lambda: 0.95, "sunny"), "rain")
        self.assertEqual(pick(lambda: 0.5, "sunny"), "sunny")


class ModifierTest(unittest.TestCase):
    def test_rain_slows_down(self):
        self.assertEqual(speed_modifier("rain"), 0.8)

    def test_snow_slows_down(self):
        self.assertEqual(speed_modifier("snow"), 0.7)

    def test_others_neutral(self):
        self.assertEqual(speed_modifier("sunny"), 1.0)
        self.assertEqual(speed_modifier("unknown"), 1.0)


class DurationTest(unittest.TestCase):
    def test_duration_within_configured_range(self):
        rng = random.Random(42)
        for weather, (low, high) in DURATIONS.items():
            for _ in range(200):
                value = duration(rng.random, weather)
                self.assertGreaterEqual(value, low)
                self.assertLessEqual(value, high)

    def test_duration_is_random_not_fixed(self):
        rng = random.Random(7)
        values = {duration(rng.random, "sunny") for _ in range(50)}
        self.assertGreater(len(values), 1)


class DeterminismTest(unittest.TestCase):
    def test_same_seed_same_sequence(self):
        self.assertEqual(simulate(123, 200), simulate(123, 200))

    def test_different_seed_differs(self):
        self.assertNotEqual(simulate(1, 200), simulate(2, 200))

    def test_replay_same_transitions(self):
        first = simulate(99, 100)
        second = simulate(99, 100)
        self.assertEqual(first, second)


class ReferenceComparisonTest(unittest.TestCase):
    def test_200_random_tables_match_reference(self):
        table_rng = random.Random(20260930)
        for _ in range(200):
            states = ["s%d" % i for i in range(table_rng.randint(2, 6))]
            table = {}
            for state in states:
                branches = table_rng.randint(1, len(states))
                targets = table_rng.sample(states, branches)
                row = [(name, table_rng.random()) for name in targets]
                if sum(w for _, w in row) <= 0:
                    row[0] = (row[0][0], 1.0)
                table[state] = row
            seed = table_rng.randint(0, 2**31)
            start = states[0]
            expected = reference_sequence(table, seed, 300, start)
            actual = implementation_sequence(table, seed, 300, start)
            self.assertEqual(actual, expected)


class PerformanceTest(unittest.TestCase):
    def test_100k_queries_under_one_second(self):
        rng = random.Random(0)
        weather = "sunny"
        start = time.perf_counter()
        for _ in range(100000):
            weather = pick(rng.random, weather)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()
