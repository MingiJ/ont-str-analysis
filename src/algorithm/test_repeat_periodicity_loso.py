import unittest

import numpy as np

from evaluate_repeat_periodicity_loso import autocorrelation_period, feature_values


class RepeatPeriodicityLOSOTest(unittest.TestCase):
    def test_autocorrelation_recovers_known_period(self) -> None:
        positions = np.arange(1200)
        signal = np.sin(2.0 * np.pi * positions / 30.0)

        period, strength = autocorrelation_period(signal, expected_period=31.0)

        self.assertAlmostEqual(30.0, period, delta=1.0)
        self.assertGreater(strength, 0.9)

    def test_feature_uses_exact_repeat_slice_not_padding(self) -> None:
        positions = np.arange(600)
        repeat = np.sin(2.0 * np.pi * positions / 30.0)
        signal = np.concatenate([np.zeros(25), repeat, np.zeros(25)])[None, :]
        metadata = [
            {
                "sample": "A",
                "source_start": "125",
                "source_end": "725",
                "window_start": "100",
                "raw_per_base_left": "10",
                "raw_per_base_right": "10",
            }
        ]

        features, periods, _ = feature_values(metadata, signal)

        self.assertEqual(600.0, features["duration"]["A"][0])
        self.assertAlmostEqual(30.0, periods[0], delta=1.0)
        self.assertAlmostEqual(20.0, features["acf_period_normalized"]["A"][0], delta=1.0)


if __name__ == "__main__":
    unittest.main()
