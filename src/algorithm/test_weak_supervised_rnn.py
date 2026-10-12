import unittest

import torch

from weak_supervised_rnn import (
    calibrate_variance_scale,
    choose_sample_split,
    fit_duration_prior,
    two_cluster_medians,
    truth_pairs_from_metadata,
    unordered_diploid_loss,
)


class WeakSupervisedRNNTest(unittest.TestCase):
    def test_loss_is_invariant_to_allele_order(self) -> None:
        prediction = torch.tensor([18.0, 19.0, 39.0, 41.0], requires_grad=True)
        log_variance = torch.zeros(4, requires_grad=True)

        forward, _ = unordered_diploid_loss(prediction, log_variance, 18.0, 40.0)
        reversed_order, _ = unordered_diploid_loss(prediction, log_variance, 40.0, 18.0)

        self.assertTrue(torch.allclose(forward, reversed_order, atol=1e-6))
        forward.backward()
        self.assertTrue(torch.isfinite(prediction.grad).all())
        self.assertTrue(torch.isfinite(log_variance.grad).all())

    def test_beta_nll_rejects_invalid_weight(self) -> None:
        with self.assertRaises(ValueError):
            unordered_diploid_loss(
                torch.tensor([18.0, 40.0]),
                torch.zeros(2),
                18.0,
                40.0,
                beta_nll=1.1,
            )

    def test_truth_reader_ignores_per_read_group_label(self) -> None:
        rows = [
            {"sample": "A", "truth_long": "41", "truth_short": "18", "group_label": "long_like"},
            {"sample": "A", "truth_long": "41", "truth_short": "18", "group_label": "short_like"},
        ]
        swapped = [dict(row, group_label="wrong") for row in rows]

        self.assertEqual(truth_pairs_from_metadata(rows), truth_pairs_from_metadata(swapped))

    def test_duration_prior_assigns_longest_windows_to_long_allele(self) -> None:
        prediction = torch.full((4,), 30.0)
        log_variance = torch.zeros(4)
        duration = torch.tensor([100.0, 400.0, 200.0, 300.0])

        _, parts = unordered_diploid_loss(
            prediction,
            log_variance,
            18.0,
            40.0,
            min_component_fraction=0.49,
            assignment_score=duration,
        )

        long_assignments = parts["posterior"][:, 1].bool()
        self.assertEqual([False, True, False, True], long_assignments.tolist())

    def test_sample_split_is_disjoint(self) -> None:
        truth = {"A": (18.0, 40.0), "B": (17.0, 41.0), "C": (20.0, 57.0)}

        train, validation, test = choose_sample_split(truth, "C", "B")

        self.assertEqual(["A"], train)
        self.assertEqual("B", validation)
        self.assertEqual("C", test)
        self.assertFalse(set(train) & {validation, test})

    def test_duration_prior_uses_training_samples_only(self) -> None:
        lengths = {
            "A": torch.tensor([100.0, 102.0, 198.0, 200.0]).numpy(),
            "B": torch.tensor([110.0, 112.0, 208.0, 210.0]).numpy(),
            "TEST": torch.tensor([1.0, 2.0, 10000.0, 20000.0]).numpy(),
        }
        truth = {"A": (10.0, 20.0), "B": (11.0, 21.0), "TEST": (1.0, 200.0)}

        first = fit_duration_prior(lengths, truth, ["A", "B"])
        lengths["TEST"] = torch.tensor([50.0, 60.0]).numpy()
        truth["TEST"] = (500.0, 600.0)
        second = fit_duration_prior(lengths, truth, ["A", "B"])

        self.assertAlmostEqual(first[0], second[0])
        self.assertAlmostEqual(first[1], second[1])
        self.assertGreater(first[1], 0.0)
        self.assertEqual({"A", "B"}, set(first[2]))

    def test_uncertainty_scale_uses_nearest_unordered_allele(self) -> None:
        predictions = torch.tensor([18.0, 20.0, 38.0, 40.0]).numpy()
        variances = torch.full((4,), 16.0).numpy()

        scale = calibrate_variance_scale(
            predictions,
            variances,
            torch.arange(4).numpy(),
            (18.0, 40.0),
        )

        self.assertAlmostEqual(0.353553, scale, places=5)

    def test_validation_cluster_centres_are_robust(self) -> None:
        short, long = two_cluster_medians(
            torch.tensor([17.0, 18.0, 19.0, 55.0, 57.0, 60.0]).numpy()
        )
        self.assertAlmostEqual(18.0, short)
        self.assertAlmostEqual(57.0, long)


if __name__ == "__main__":
    unittest.main()
