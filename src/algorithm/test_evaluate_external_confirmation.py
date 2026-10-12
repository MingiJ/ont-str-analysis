from __future__ import annotations

import unittest

import numpy as np

try:
    from evaluate_external_confirmation import (
        assert_external_truth_is_hidden,
        predict_from_features,
        score_predictions,
    )
except ImportError:  # pragma: no cover
    from .evaluate_external_confirmation import (
        assert_external_truth_is_hidden,
        predict_from_features,
        score_predictions,
    )


class ExternalConfirmationTests(unittest.TestCase):
    def test_external_prediction_rejects_embedded_truth(self) -> None:
        with self.assertRaisesRegex(ValueError, "contains genotype truth"):
            assert_external_truth_is_hidden(
                [{"sample": "external", "truth_short": "16", "truth_long": "44"}]
            )

    def test_prediction_uses_only_development_truth(self) -> None:
        development_truth = {
            "a": (10.0, 20.0),
            "b": (12.0, 24.0),
            "c": (14.0, 28.0),
        }
        development = {
            feature: {
                "a": np.array([100.0, 101.0, 200.0, 201.0]),
                "b": np.array([120.0, 121.0, 240.0, 241.0]),
                "c": np.array([140.0, 141.0, 280.0, 281.0]),
            }
            for feature in ("duration", "acf_period_normalized")
        }
        external = {
            feature: {"external": np.array([160.0, 161.0, 320.0, 321.0])}
            for feature in ("duration", "acf_period_normalized")
        }
        first = predict_from_features(development, development_truth, external)
        second = predict_from_features(development, development_truth, external)
        self.assertEqual(first, second)
        self.assertEqual(
            {row["feature"] for row in first},
            {"duration", "acf_period_normalized"},
        )
        self.assertTrue(all(row["development_samples"] == 3 for row in first))

    def test_scoring_sorts_unordered_prediction_pairs(self) -> None:
        predictions = [
            {
                "sample": "NA13512",
                "feature": "duration",
                "pred_short": "45",
                "pred_long": "15",
            }
        ]
        scored, summary = score_predictions(predictions, {"NA13512": (16.0, 44.0)})
        self.assertEqual(scored[0]["short_abs_error"], "1.000000")
        self.assertEqual(scored[0]["long_abs_error"], "1.000000")
        self.assertEqual(scored[0]["allele_mae"], "1.000000")
        self.assertEqual(
            summary,
            [{"feature": "duration", "external_samples": 1, "allele_mae": "1.000000"}],
        )


if __name__ == "__main__":
    unittest.main()
