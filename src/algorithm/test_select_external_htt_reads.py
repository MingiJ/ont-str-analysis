from __future__ import annotations

import unittest

try:
    from alignment_signal_bounds import Alignment, LOCUS_START_0
    from select_external_htt_reads import eligible_read_ids
except ImportError:  # pragma: no cover
    from .alignment_signal_bounds import Alignment, LOCUS_START_0
    from .select_external_htt_reads import eligible_read_ids


def alignment(read_id: str, *, mapq: int = 60, reference_start: int | None = None) -> Alignment:
    return Alignment(
        read_id=read_id,
        flag=0,
        reference_start=LOCUS_START_0 - 500 if reference_start is None else reference_start,
        mapq=mapq,
        cigar="1200M",
    )


class SelectExternalHttReadsTests(unittest.TestCase):
    def test_requires_full_flanks_mapq_and_unique_alignment(self) -> None:
        alignments = {
            "pass": [alignment("pass")],
            "low-mapq": [alignment("low-mapq", mapq=10)],
            "partial": [alignment("partial", reference_start=LOCUS_START_0)],
            "multiple": [alignment("multiple"), alignment("multiple")],
        }
        self.assertEqual(
            eligible_read_ids(
                alignments,
                flank_bp=112,
                min_mapq=20,
                max_reads=0,
                selection_seed="test",
            ),
            ["pass"],
        )

    def test_cap_is_deterministic_and_seeded(self) -> None:
        alignments = {read_id: [alignment(read_id)] for read_id in ("a", "b", "c", "d")}
        first = eligible_read_ids(
            alignments, flank_bp=112, min_mapq=20, max_reads=2, selection_seed="test"
        )
        second = eligible_read_ids(
            dict(reversed(list(alignments.items()))),
            flank_bp=112,
            min_mapq=20,
            max_reads=2,
            selection_seed="test",
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)


if __name__ == "__main__":
    unittest.main()
