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
