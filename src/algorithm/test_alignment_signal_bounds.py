import unittest

import numpy as np

from alignment_signal_bounds import (
    canonical_read_id,
    boundary_quality,
    cigar_lengths,
    event_end_bases,
    event_start_to_raw,
    longest_consecutive_motif,
    reference_boundary_to_query,
)
from build_independent_truth_manifest import load_truth_samples
from signal_windows import source_boundaries
from pathlib import Path
from tempfile import TemporaryDirectory


class AlignmentSignalBoundsTest(unittest.TestCase):
    def test_canonicalizes_legacy_alignment_suffix(self) -> None:
        read_id = "00d1414b-f1a8-4ac9-8fd0-05e8e239a5eb"
        self.assertEqual(read_id, canonical_read_id(read_id))
        self.assertEqual(read_id, canonical_read_id(f"{read_id}_Basecall_Alignment_template"))

    def test_maps_reference_boundaries_through_indels(self) -> None:
        cigar = "5H3S10M2I5M1D10M4S2H"
        self.assertEqual(3, reference_boundary_to_query(100, cigar, 100))
        self.assertEqual(13, reference_boundary_to_query(110, cigar, 100))
        self.assertEqual(16, reference_boundary_to_query(111, cigar, 100))
        self.assertEqual(20, reference_boundary_to_query(115, cigar, 100))
        self.assertEqual(20, reference_boundary_to_query(116, cigar, 100))
        self.assertEqual(21, reference_boundary_to_query(117, cigar, 100))

    def test_counts_reference_query_and_clipping_lengths(self) -> None:
        self.assertEqual((26, 34, 5, 7, 7), cigar_lengths("5H3S10M2I5M1D10M4S2H"))

    def test_counts_longest_cag_run_across_phases(self) -> None:
        self.assertEqual(3, longest_consecutive_motif("AACAGCAGCAGCAACAG"))

    def test_infers_albacore_event_offset_from_sequence_length(self) -> None:
        moves = np.asarray([0, 1, 0, 2, 1], dtype=np.int64)
        self.assertEqual([4, 5, 5, 7, 8], event_end_bases(moves, 8).tolist())
        self.assertEqual([5, 6, 6, 8, 9], event_end_bases(moves, 9).tolist())

    def test_rejects_implausible_event_offset(self) -> None:
        with self.assertRaises(ValueError):
            event_end_bases(np.asarray([1, 1]), 100)

    def test_converts_integer_sample_relative_event_start(self) -> None:
        self.assertEqual(
            5432,
            event_start_to_raw(
                5432,
                integer_start=True,
                sampling_rate=4000.0,
                raw_start=5_000_000,
                raw_len=70_000,
            ),
        )

    def test_converts_seconds_absolute_event_start(self) -> None:
        self.assertEqual(
            3000,
            event_start_to_raw(
                1250.75,
                integer_start=False,
                sampling_rate=4000.0,
                raw_start=5_000_000,
                raw_len=70_000,
            ),
        )

    def test_boundary_quality_accepts_consistent_single_alignment(self) -> None:
        passed, reason, rates = boundary_quality(
            (100, 200, 260, 360),
            (1000, 2200, 2920, 4020),
            1,
        )
        self.assertTrue(passed)
        self.assertEqual("pass", reason)
        self.assertAlmostEqual(12.0, rates[1])

    def test_boundary_quality_rejects_ambiguous_or_inconsistent_mapping(self) -> None:
        passed, reason, _ = boundary_quality(
            (100, 200, 260, 360),
            (1000, 2100, 5700, 6800),
            2,
        )
        self.assertFalse(passed)
        self.assertIn("multiple_full_flank_alignments", reason)
        self.assertIn("discordant_repeat_rate", reason)

    def test_signal_extractor_selects_repeat_boundaries(self) -> None:
        row = {
            "signal_window_start": "100",
            "signal_repeat_start": "200",
            "signal_repeat_end": "500",
            "signal_window_end": "700",
        }
        self.assertEqual((100, 700), source_boundaries(row, "window"))
        self.assertEqual((200, 500), source_boundaries(row, "repeat"))

    def test_truth_manifest_excludes_unlabelled_and_nonprimary_samples(self) -> None:
        content = (
            "sample\ttruth_long\ttruth_short\tinclude_primary\n"
            "A\t41\t18\t1\n"
            "B\t\t\t0\n"
            "C\t50\t20\t0\n"
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "truth.tsv"
            path.write_text(content)
            self.assertEqual([("A", 41, 18)], load_truth_samples(path, None))

    def test_truth_manifest_rejects_unknown_requested_sample(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "truth.tsv"
            path.write_text("sample\ttruth_long\ttruth_short\tinclude_primary\nA\t41\t18\t1\n")
            with self.assertRaises(ValueError):
                load_truth_samples(path, {"UNKNOWN"})


if __name__ == "__main__":
    unittest.main()
