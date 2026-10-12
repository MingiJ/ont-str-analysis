from __future__ import annotations

import unittest

try:
    from dorado_move_signal_bounds import (
        decode_move_values,
        move_table_base_boundaries,
        parse_move_tag,
        parse_sam_line,
    )
except ImportError:  # pragma: no cover
    from .dorado_move_signal_bounds import (
        decode_move_values,
        move_table_base_boundaries,
        parse_move_tag,
        parse_sam_line,
    )


class DoradoMoveSignalBoundsTests(unittest.TestCase):
    def test_decodes_signed_byte_overflow_runs(self) -> None:
        self.assertEqual(decode_move_values([1, 127, 13, 0, -128, -2]), [1, 140, 0, -130])

    def test_rejects_unterminated_overflow_run(self) -> None:
        with self.assertRaisesRegex(ValueError, "no terminating"):
            decode_move_values([1, 127])

    def test_maps_base_boundaries_with_trim_and_signal_end(self) -> None:
        # stride=5; four bases emitted from blocks 0, 2, 3, and 5.
        boundaries = move_table_base_boundaries((5, 1, 0, 1, 1, 0, 1), 100, 134, 4)
        self.assertEqual(boundaries, (100, 110, 115, 125, 134))

    def test_supports_multiple_bases_emitted_in_one_block(self) -> None:
        boundaries = move_table_base_boundaries((5, 2, 0, 1), 10, 25, 3)
        self.assertEqual(boundaries, (10, 10, 20, 25))

    def test_rejects_move_sequence_length_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "move/sequence length mismatch"):
            move_table_base_boundaries((5, 1, 0, 1), 10, 25, 3)

    def test_parses_dorado_sam_tags(self) -> None:
        sam = (
            "read-1\t0\tchr4\t3074764\t60\t5M\t*\t0\t0\tACGTA\tFFFFF"
            "\tmv:B:c,5,1,1,1,1,1\tts:i:20\tns:i:50"
        )
        record = parse_sam_line(sam)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.move_tag, (5, 1, 1, 1, 1, 1))
        self.assertEqual(record.trim_start, 20)
        self.assertEqual(record.signal_end, 50)
        self.assertEqual(record.sequence, "ACGTA")

    def test_parses_move_array_subtype(self) -> None:
        self.assertEqual(parse_move_tag("c,5,1,0,1"), (5, 1, 0, 1))
        with self.assertRaisesRegex(ValueError, "unsupported"):
            parse_move_tag("C,5,1")


if __name__ == "__main__":
    unittest.main()
