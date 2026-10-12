import unittest

import numpy as np

from uncertainty_alleles import call_alleles_with_uncertainty


class UncertaintyAllelesTest(unittest.TestCase):
    def test_resolves_well_separated_alleles(self) -> None:
        values = np.asarray([17.8, 18.0, 18.2, 39.7, 40.0, 40.3] * 8)
        variances = np.full(values.shape, 0.25)

        call = call_alleles_with_uncertainty(values, variances)

        self.assertTrue(call.resolved)
        self.assertAlmostEqual(18.0, call.pred_short, delta=0.5)
        self.assertAlmostEqual(40.0, call.pred_long, delta=0.5)

    def test_abstains_when_one_component_is_sufficient(self) -> None:
        values = np.linspace(18.8, 19.2, 40)
        variances = np.full(values.shape, 1.0)

        call = call_alleles_with_uncertainty(values, variances)

        self.assertFalse(call.resolved)
        self.assertAlmostEqual(call.pred_short, call.pred_long)
        self.assertEqual("low", call.confidence)

    def test_high_uncertainty_outlier_has_limited_influence(self) -> None:
        values = np.asarray([18.0] * 20 + [40.0] * 20 + [100.0])
        variances = np.asarray([0.25] * 40 + [2500.0])

        call = call_alleles_with_uncertainty(values, variances)

        self.assertTrue(call.resolved)
        self.assertAlmostEqual(18.0, call.pred_short, delta=1.0)
        self.assertAlmostEqual(40.0, call.pred_long, delta=1.0)


if __name__ == "__main__":
    unittest.main()
