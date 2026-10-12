import unittest

from call_alleles import add_confidence


class CallAllelesTest(unittest.TestCase):
    def test_marks_unresolved_alleles_low_confidence(self) -> None:
        row = {
            "pred_long": 16,
            "pred_short": 15,
            "support_long": 16,
            "support_short": 17,
            "rows_available": 93,
            "rows_used": 33,
            "rows_quality_filtered": 60,
        }

        result = add_confidence(row)

        self.assertEqual("low", result["confidence"])
        self.assertIn("unresolved_allele_separation", result["confidence_reason"])
        self.assertIn("mapping_quality_filtering", result["confidence_reason"])


if __name__ == "__main__":
    unittest.main()
