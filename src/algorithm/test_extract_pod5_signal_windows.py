from __future__ import annotations

import unittest

import numpy as np

try:
    from extract_pod5_signal_windows import pack_window
except ImportError:  # pragma: no cover
    from .extract_pod5_signal_windows import pack_window


class ExtractPod5SignalWindowsTests(unittest.TestCase):
    def test_packs_normalized_window_and_mask(self) -> None:
        raw = np.arange(20, dtype=np.float32)
        signal, mask, metrics = pack_window(raw, 5, 10, padding=2, max_signal_len=10)
        self.assertEqual(metrics["window_start"], 3)
        self.assertEqual(metrics["window_end"], 12)
        self.assertEqual(metrics["stored_len"], 9)
        self.assertEqual(metrics["truncated"], 0)
        self.assertEqual(int(mask.sum()), 9)
        self.assertEqual(signal.shape, (10,))
        self.assertAlmostEqual(float(np.median(signal[:9])), 0.0, places=6)

    def test_truncates_long_window_deterministically(self) -> None:
        raw = np.arange(30, dtype=np.float32)
        first, first_mask, metrics = pack_window(raw, 2, 22, padding=0, max_signal_len=5)
        second, second_mask, _ = pack_window(raw, 2, 22, padding=0, max_signal_len=5)
        self.assertEqual(metrics["window_span"], 20)
        self.assertEqual(metrics["truncated"], 1)
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(first_mask, second_mask)

    def test_rejects_empty_bounded_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty signal window"):
            pack_window(np.arange(10), 20, 30, padding=0, max_signal_len=10)


if __name__ == "__main__":
    unittest.main()
