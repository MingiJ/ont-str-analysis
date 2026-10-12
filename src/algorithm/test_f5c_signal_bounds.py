from __future__ import annotations

import unittest

try:
    from f5c_signal_bounds import boundary_qc, segment_span
except ImportError:  # pragma: no cover
    from .f5c_signal_bounds import boundary_qc, segment_span


class F5cSignalBoundsTests(unittest.TestCase):
    def test_segment_span_uses_raw_extrema(self) -> None:
        events = [(100 + index, 1000 + index * 10, 1008 + index * 10) for index in range(10)]
        self.assertEqual(segment_span(events, 102, 107, min_events=5), (1020, 1068, 5))

    def test_boundary_qc_accepts_consistent_rates(self) -> None:
        passed, reason, rates = boundary_qc(1120, 580, 1120, (112, 58, 112), 1)
        self.assertTrue(passed)
        self.assertEqual(reason, "pass")
        self.assertAlmostEqual(rates[3], 1.0)

    def test_boundary_qc_uses_expanded_query_span(self) -> None:
        passed, reason, rates = boundary_qc(1120, 2100, 1120, (112, 210, 112), 1)
        self.assertTrue(passed)
        self.assertEqual(reason, "pass")
        self.assertAlmostEqual(rates[3], 1.0)

    def test_boundary_qc_rejects_multiple_alignments(self) -> None:
        passed, reason, _ = boundary_qc(1120, 580, 1120, (112, 58, 112), 2)
        self.assertFalse(passed)
        self.assertIn("multiple_full_flank_alignments", reason)


if __name__ == "__main__":
    unittest.main()
