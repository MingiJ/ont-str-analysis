from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from audit_mastr_archive_mapping import audit_rows, best_paf_matches
except ImportError:  # pragma: no cover
    from .audit_mastr_archive_mapping import audit_rows, best_paf_matches


class AuditMastrArchiveMappingTests(unittest.TestCase):
    def test_filters_weak_paf_matches_and_keeps_best(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.paf"
            path.write_text(
                "r1\t100\t0\t95\t+\tMASTR_P|a\t100\t0\t95\t90\t95\t40\n"
                "r1\t100\t0\t98\t+\tMASTR_N|b\t100\t0\t98\t95\t98\t60\n"
                "r2\t100\t0\t50\t+\tMASTR_P|c\t100\t0\t50\t49\t50\t60\n"
            )
            self.assertEqual(
                best_paf_matches(path, min_identity=0.85, min_query_coverage=0.80),
                {"r1": "MASTR_N"},
            )

    def test_requires_support_and_concordance_per_sample(self) -> None:
        assignments = {"p1": "P", "p2": "P", "n1": "N", "n2": "N"}
        matches = {"p1": "P", "p2": "P", "n1": "N", "n2": "P"}
        rows, passed = audit_rows(
            assignments, matches, min_matches_per_sample=2, min_concordance=0.90
        )
        self.assertFalse(passed)
        self.assertEqual(rows[0]["status"], "fail")
        self.assertEqual(rows[1]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
