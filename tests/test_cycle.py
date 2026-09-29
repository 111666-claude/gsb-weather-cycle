import unittest

from weathercycle.cycle import TABLE, pick, speed_modifier, weight_sum


class PickTest(unittest.TestCase):
    def test_low_roll_picks_first(self):
        self.assertEqual(pick(lambda: 0.0, "sunny"), "sunny")

    def test_second_branch(self):
        self.assertEqual(pick(lambda: 0.7, "sunny"), "rain")

    def test_single_branch(self):
        self.assertEqual(pick(lambda: 0.9, "snow"), "snow")

    def test_table_has_three_states(self):
        self.assertEqual(sorted(TABLE), ["rain", "snow", "sunny"])


class ModifierTest(unittest.TestCase):
    def test_sunny_is_neutral(self):
        self.assertEqual(speed_modifier("sunny"), 1.0)

    def test_weight_sum_positive(self):
        for state in TABLE:
            self.assertGreater(weight_sum(state), 0)


if __name__ == "__main__":
    unittest.main()


import random
import time

from weathercycle.cycle import (
    DURATION_RANGES,
    WeatherCycle,
    normalize_rows,
    sample_duration,
    weather_sequence,
)


class NormalizationTest(unittest.TestCase):
    def test_every_row_sums_to_one(self):
        rows = normalize_rows(TABLE)
        for state, branches in rows.items():
            self.assertAlmostEqual(sum(weight for _, weight in branches), 1.0)

    def test_deficient_row_scaled_proportionally(self):
        rows = normalize_rows(TABLE)
        names = [name for name, _ in rows["sunny"]]
        weights = [weight for _, weight in rows["sunny"]]
        self.assertEqual(names, ["sunny", "rain"])
        self.assertAlmostEqual(weights[0], 2.0 / 3.0)
        self.assertAlmostEqual(weights[1], 1.0 / 3.0)
        self.assertAlmostEqual(weights[0] / weights[1], 2.0)

    def test_pick_does_not_collapse_tail_to_last_branch(self):
        # 权重和 0.90：roll=0.92 落在缺失的尾部。旧实现会错误回落到最后一项 z；
        # 归一化后各分支按比例占满 [0,1)，0.92 仍在首分支 x 内
        # （累计边界 0.85/0.90≈0.9444）。
        table = {"a": [("x", 0.85), ("y", 0.0), ("z", 0.05)]}
        self.assertEqual(pick(lambda: 0.92, "a", table), "x")
        # 权重和 0.90、中段有正权重时，旧实现同样把尾部 roll 错判给 z；
        # 归一化后 0.95 落在中段 y（累计边界 0.87/0.90≈0.9667）。
        table2 = {"a": [("x", 0.85), ("y", 0.02), ("z", 0.03)]}
        self.assertEqual(pick(lambda: 0.95, "a", table2), "y")

    def test_weights_above_one_are_scaled_down(self):
        table = {"a": [("x", 2.0), ("y", 6.0), ("z", 2.0)]}
        rows = normalize_rows(table)
        weights = [weight for _, weight in rows["a"]]
        for actual, expected in zip(weights, [0.2, 0.6, 0.2]):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(pick(lambda: 0.5, "a", table), "y")

    def test_every_positive_branch_is_reachable(self):
        rows = normalize_rows(TABLE)
        rng = random.Random(1234)
        for state, branches in rows.items():
            seen = {pick(rng.random, state) for _ in range(2000)}
            positive = {name for name, weight in branches if weight > 0}
            self.assertEqual(seen, positive)


class ModifierCoefficientTest(unittest.TestCase):
    def test_rain_slows_down(self):
        self.assertEqual(speed_modifier("rain"), 0.8)
        self.assertLess(speed_modifier("rain"), 1.0)

    def test_snow_slows_down_more(self):
        self.assertEqual(speed_modifier("snow"), 0.7)
        self.assertLess(speed_modifier("snow"), speed_modifier("rain"))

    def test_other_weather_is_neutral(self):
        for weather in ("sunny", "cloudy", "fog"):
            self.assertEqual(speed_modifier(weather), 1.0)

    def test_modifier_does_not_change_transitions(self):
        # 修正系数只是纯函数查表，不参与转移：同种子、同 roll 的转移结果一致。
        table = {"a": [("a", 0.5), ("b", 0.5)]}
        for roll in (0.0, 0.4, 0.5, 0.99):
            first = pick(lambda r=roll: r, "a", table)
            second = pick(lambda r=roll: r, "a", table)
            self.assertEqual(first, second)


class DeterminismTest(unittest.TestCase):
    def test_same_seed_same_sequence(self):
        seq_a = weather_sequence(2026, "sunny", 500)
        seq_b = weather_sequence(2026, "sunny", 500)
        self.assertEqual(seq_a, seq_b)

    def test_distinct_seeds_distinct_streams(self):
        seq_a = weather_sequence(1, "sunny", 200)
        seq_b = weather_sequence(2, "sunny", 200)
        self.assertNotEqual(seq_a, seq_b)

    def test_batch_replay_is_identical(self):
        cycle = WeatherCycle(777, "rain")
        first = cycle.replay(50)
        second = cycle.replay(50)
        self.assertEqual(first, second)
        third = WeatherCycle(777, "rain").replay(50)
        self.assertEqual(first, third)

    def test_duration_within_configured_range_and_random(self):
        rng = random.Random(42)
        values = [sample_duration(rng, "rain") for _ in range(100)]
        low, high = DURATION_RANGES["rain"]
        self.assertTrue(all(low <= value <= high for value in values))
        self.assertGreater(len(set(values)), 1)
        self.assertFalse(all(value == values[0] for value in values))

    def test_duration_stream_independent_from_transitions(self):
        cycle_a = WeatherCycle(99, "sunny")
        spells = cycle_a.replay(20)
        durations = [duration for _, duration in spells]
        # 只走转移、不碰持续时长流之后，天气序列仍与同种子完全一致。
        transition_cycle = WeatherCycle(99, "sunny")
        transition_only = [transition_cycle.next_weather() for _ in range(20)]
        self.assertEqual([weather for weather, _ in spells], transition_only)
        self.assertTrue(all(DURATION_RANGES[w][0] <= duration <= DURATION_RANGES[w][1]
                            for w, duration in spells))
        # 同种子持续时长同样可复现。
        again = WeatherCycle(99, "sunny").replay(20)
        self.assertEqual(durations, [duration for _, duration in again])


class ReferenceCrossCheckTest(unittest.TestCase):
    @staticmethod
    def _reference_table(rng):
        # 独立参考实现：随机 1~4 个状态、1~4 个分支，权重取值覆盖 0、不足 1
        # 与超过 1 的情形（不保证每个名字都是状态，转移只按分支名走）。
        states = ["s%d" % i for i in range(rng.randint(1, 4))]
        table = {}
        for state in states:
            branches = []
            for _ in range(rng.randint(1, 4)):
                branches.append((rng.choice(states), rng.choice([0.0, 0.1, 0.3, 0.5, 1.5, 2.0])))
            if not any(weight > 0 for _, weight in branches):
                branches[0] = (branches[0][0], 0.5)
            table[state] = branches
        return table

    @staticmethod
    def _reference_sequence(seed, table, start, steps):
        # 口径：逐行「归一化 + 累计分布采样」，每步独立 uniform(0,1)。
        rng = random.Random(seed)
        normalized = {}
        for state, branches in table.items():
            total = sum(weight for _, weight in branches)
            normalized[state] = [(name, weight / total) for name, weight in branches]
        state = start
        sequence = []
        for _ in range(steps):
            roll = rng.random()
            cumulative = 0.0
            for name, weight in normalized[state]:
                cumulative += weight
                if roll < cumulative:
                    state = name
                    break
            else:
                state = normalized[state][-1][0]
            sequence.append(state)
        return sequence

    def test_200_random_tables_match_reference(self):
        case_rng = random.Random(20260930)
        mismatches = 0
        for _ in range(200):
            table = self._reference_table(case_rng)
            seed = case_rng.randrange(1 << 62)
            start = case_rng.choice(list(table))
            steps = case_rng.randint(1, 120)
            expected = self._reference_sequence(seed, table, start, steps)
            actual = weather_sequence(seed, start, steps, table)
            if actual != expected:
                mismatches += 1
        self.assertEqual(mismatches, 0)


class ScaleTest(unittest.TestCase):
    def test_100k_picks_under_one_second(self):
        rng = random.Random(0)
        state = "sunny"
        started = time.perf_counter()
        for _ in range(100_000):
            state = pick(rng.random, state)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()
