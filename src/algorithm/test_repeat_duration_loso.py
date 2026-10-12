import unittest

import numpy as np

from evaluate_repeat_duration_loso import durations_from_metadata, evaluate_loso, predict_holdout


class RepeatDurationLOSOTest(unittest.TestCase):
    @staticmethod
    def rows() -> list[dict[str, str]]:
        rows = []
        for sample, truth, durations in (
            ("A", (10, 20), (100, 102, 198, 200)),
            ("B", (11, 21), (110, 112, 208, 210)),
            ("TEST", (12, 22), (120, 122, 218, 220)),
        ):
            for index, duration in enumerate(durations):
                rows.append(
                    {
                        "sample": sample,
                        "truth_short": str(truth[0]),
                        "truth_long": str(truth[1]),
                        "source_span_abs": str(duration),
                        "group_label": "deliberately_ignored",
                        "read_id": f"{sample}-{index}",
                    }
                )
        return rows

    def test_holdout_prediction_does_not_use_holdout_truth(self) -> None:
        rows = self.rows()
        durations = durations_from_metadata(rows, "source_span_abs")
        truth = {"A": (10.0, 20.0), "B": (11.0, 21.0), "TEST": (12.0, 22.0)}
        first = predict_holdout(durations, truth, ["A", "B"], "TEST")
        truth["TEST"] = (500.0, 900.0)
        second = predict_holdout(durations, truth, ["A", "B"], "TEST")

        self.assertAlmostEqual(first["pred_short"], second["pred_short"])
        self.assertAlmostEqual(first["pred_long"], second["pred_long"])

    def test_group_labels_do_not_change_loso_predictions(self) -> None:
        rows = self.rows()
        first = evaluate_loso(rows)
        for row in rows:
            row["group_label"] = "opposite_label"
        second = evaluate_loso(rows)

        np.testing.assert_allclose(
            [float(row["pred_short"]) for row in first],
            [float(row["pred_short"]) for row in second],
        )
        np.testing.assert_allclose(
            [float(row["pred_long"]) for row in first],
            [float(row["pred_long"]) for row in second],
        )


if __name__ == "__main__":
    unittest.main()
