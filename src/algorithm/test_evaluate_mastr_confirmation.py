from __future__ import annotations

import unittest

try:
    from evaluate_mastr_confirmation import (
        EXPECTED_SAMPLES,
        build_mastr_decision,
        validate_external_cohort,
    )
except ImportError:  # pragma: no cover
    from .evaluate_mastr_confirmation import (
        EXPECTED_SAMPLES,
        build_mastr_decision,
        validate_external_cohort,
    )


def score_rows(
    *,
    acf_allele_mae: float,
    expanded_long_error: float,
    duration_allele_mae: float,
) -> list[dict[str, str]]:
    rows = []
    for index, sample in enumerate(EXPECTED_SAMPLES):
        for feature, allele_mae in (
            ("acf_period_normalized", acf_allele_mae),
            ("duration", duration_allele_mae),
        ):
            rows.append(
                {
                    "sample": sample,
                    "feature": feature,
                    "pred_short": str(20 + index),
                    "pred_long": str(22 + index),
                    "allele_mae": str(allele_mae),
                    "long_abs_error": str(
                        expanded_long_error if sample in ("MASTR_E1", "MASTR_E2") else 1.0
                    ),
                }
            )
    return rows


class MastrConfirmationTests(unittest.TestCase):
    def test_requires_exact_cohort_and_minimum_qc_rows(self) -> None:
        complete = [
            {"sample": sample} for sample in EXPECTED_SAMPLES for _ in range(6)
        ]
        validate_external_cohort(complete)
        with self.assertRaisesRegex(ValueError, "below frozen minimum"):
            validate_external_cohort(complete[:-1])
        with self.assertRaisesRegex(ValueError, "cohort mismatch"):
            validate_external_cohort(complete + [{"sample": "unexpected"}] * 6)

    def test_primary_thresholds_pass_at_boundaries(self) -> None:
        decision, passed = build_mastr_decision(
            score_rows(acf_allele_mae=3.0, expanded_long_error=5.0, duration_allele_mae=99.0)
        )
        self.assertTrue(passed)
        self.assertEqual(decision[-1]["value"], "pass")

    def test_duration_cannot_change_primary_failure(self) -> None:
        decision, passed = build_mastr_decision(
            score_rows(acf_allele_mae=3.01, expanded_long_error=1.0, duration_allele_mae=0.0)
        )
        self.assertFalse(passed)
        self.assertEqual(decision[-1]["value"], "fail")

    def test_expanded_long_error_is_independent_gate(self) -> None:
        _, passed = build_mastr_decision(
            score_rows(acf_allele_mae=1.0, expanded_long_error=5.01, duration_allele_mae=0.0)
        )
        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
