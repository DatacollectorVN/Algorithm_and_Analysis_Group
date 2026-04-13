"""Tests for synthetic data and normalization."""

import unittest

from services.dataset import Corpuses
from services.dto import RawProfile
from services.helper import ValidationError


class TestPipeline(unittest.TestCase):
    def test_degree_unknown(self) -> None:
        with self.assertRaises(ValidationError):
            Corpuses.degree_to_rank("not_a_real_degree")

    def test_domain_unknown(self) -> None:
        with self.assertRaises(ValidationError):
            Corpuses.domain_to_index("unknown_domain")

    def test_minmax_constant_dimension(self) -> None:
        stats = Corpuses.compute_scaling_stats(
            [(1.0, 2.0, 3.0, 4.0, 5.0), (1.0, 2.0, 3.0, 4.0, 5.0)]
        )
        v = Corpuses.apply_minmax((1.0, 2.0, 3.0, 4.0, 5.0), stats)
        self.assertEqual(v, (0.0, 0.0, 0.0, 0.0, 0.0))

    def test_synthetic_in_ranges(self) -> None:
        for p in Corpuses.iter_synthetic_profiles(50, seed=1):
            self.assertTrue(18 <= p.age <= 70)
            self.assertGreaterEqual(p.monthly_income, 5.0)
            self.assertLessEqual(p.monthly_income, 100.0)
            self.assertGreaterEqual(p.daily_learning_hours, 0.0)
            self.assertLessEqual(p.daily_learning_hours, 8.0)

    def test_empty_corpus_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Corpuses.build_normalized_corpus([])

    def test_raw_to_prevector_roundtrip_normalized(self) -> None:
        raw = RawProfile("t", 30.0, 50.0, 4.0, "bachelor", "software")
        pre = Corpuses.raw_to_prevector(raw)
        stats = Corpuses.compute_scaling_stats([pre])
        norm = Corpuses.apply_minmax(pre, stats)
        self.assertEqual(norm, (0.0, 0.0, 0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
