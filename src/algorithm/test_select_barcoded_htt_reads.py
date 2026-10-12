from __future__ import annotations

import unittest

try:
    from select_barcoded_htt_reads import normalize_barcode, sam_barcode
except ImportError:  # pragma: no cover
    from .select_barcoded_htt_reads import normalize_barcode, sam_barcode


class SelectBarcodedHttReadsTests(unittest.TestCase):
    def test_normalizes_plain_and_kit_prefixed_barcodes(self) -> None:
        self.assertEqual(normalize_barcode("barcode9"), "barcode09")
        self.assertEqual(normalize_barcode("SQK-NBD114-24_barcode12"), "barcode12")
        self.assertIsNone(normalize_barcode("unclassified"))

    def test_reads_bc_sam_tag(self) -> None:
        fields = ["read"] * 11 + ["NM:i:1", "BC:Z:SQK-NBD114-24_barcode09"]
        self.assertEqual(sam_barcode(fields), "barcode09")


if __name__ == "__main__":
    unittest.main()
