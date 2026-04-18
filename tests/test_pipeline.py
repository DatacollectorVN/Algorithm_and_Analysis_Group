"""Tests for synthetic data and normalization."""

import unittest

from services.constants import DOMAIN_CATALOG, VECTOR_DIM
from services.dataset import Corpuses
from services.dto import Profile
from services.helper import ValidationError


def _make_raw(domain: str = "software", degree: str = "bachelor") -> Profile:
    return Profile(1, 30.0, 50.0, 4.0, degree, domain)


def _prevec_14() -> tuple[float, ...]:
    """A representative 14-float pre-vector (bachelor / software)."""
    return Corpuses.raw_to_prevector(_make_raw())


class TestPipeline(unittest.TestCase):
    def test_degree_unknown(self) -> None:
        with self.assertRaises(ValidationError):
            Corpuses.degree_to_rank("not_a_real_degree")

    def test_domain_unknown(self) -> None:
        with self.assertRaises(ValidationError):
            Corpuses.domain_to_onehot("unknown_domain")

    def test_minmax_constant_dimension(self) -> None:
        pre = _prevec_14()
        stats = Corpuses.compute_scaling_stats([pre, pre])
        v = Corpuses.apply_minmax(pre, stats)
        # Numeric dims: all constant → 0.0; domain bits: pass through unchanged
        self.assertEqual(v[:4], (0.0, 0.0, 0.0, 0.0))
        # domain bits are unchanged (not scaled)
        self.assertEqual(v[4:], pre[4:])

    def test_synthetic_in_ranges(self) -> None:
        for i, p in enumerate(Corpuses.iter_synthetic_profiles(50, seed=1), start=1):
            self.assertEqual(p.profile_id, i)
            self.assertTrue(18 <= p.age <= 70)
            self.assertGreaterEqual(p.monthly_income, 5.0)
            self.assertLessEqual(p.monthly_income, 100.0)
            self.assertGreaterEqual(p.daily_learning_hours, 0.0)
            self.assertLessEqual(p.daily_learning_hours, 8.0)

    def test_empty_corpus_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Corpuses.build_normalized_corpus([])

    def test_raw_to_prevector_length(self) -> None:
        pre = _prevec_14()
        self.assertEqual(len(pre), VECTOR_DIM)

    def test_raw_to_prevector_domain_bits(self) -> None:
        pre = Corpuses.raw_to_prevector(_make_raw(domain="software"))
        domain_bits = pre[4:]
        self.assertEqual(len(domain_bits), len(DOMAIN_CATALOG))
        self.assertEqual(domain_bits[0], 1.0)  # software is index 0
        self.assertEqual(sum(domain_bits), 1.0)

    def test_raw_to_prevector_single_profile_normalizes_to_zero_numeric(self) -> None:
        raw = _make_raw()
        pre = Corpuses.raw_to_prevector(raw)
        stats = Corpuses.compute_scaling_stats([pre])
        norm = Corpuses.apply_minmax(pre, stats)
        # Numeric dims constant → 0.0
        self.assertEqual(norm[:4], (0.0, 0.0, 0.0, 0.0))
        # Domain bits pass through
        self.assertEqual(norm[4:], pre[4:])


class TestOneHotEncoding(unittest.TestCase):
    def test_domain_to_onehot_length(self) -> None:
        for domain in DOMAIN_CATALOG:
            bits = Corpuses.domain_to_onehot(domain)
            self.assertEqual(len(bits), len(DOMAIN_CATALOG))

    def test_domain_to_onehot_exactly_one_hot(self) -> None:
        for domain in DOMAIN_CATALOG:
            bits = Corpuses.domain_to_onehot(domain)
            self.assertEqual(sum(bits), 1.0)
            self.assertEqual(bits.count(1.0), 1)
            self.assertEqual(bits.count(0.0), len(DOMAIN_CATALOG) - 1)

    def test_domain_to_onehot_correct_position(self) -> None:
        for idx, domain in enumerate(DOMAIN_CATALOG):
            bits = Corpuses.domain_to_onehot(domain)
            self.assertEqual(bits[idx], 1.0)
            for j, v in enumerate(bits):
                if j != idx:
                    self.assertEqual(v, 0.0)

    def test_domain_to_onehot_unknown_raises(self) -> None:
        with self.assertRaises(ValidationError):
            Corpuses.domain_to_onehot("not_a_domain")

    def test_corpus_vector_dimension(self) -> None:
        raws = list(Corpuses.iter_synthetic_profiles(20, seed=7))
        corpus = Corpuses.from_raw(raws)
        for np in corpus.vectorized_profiles:
            self.assertEqual(len(np.vector), VECTOR_DIM)

    def test_corpus_domain_bits_mutual_exclusivity(self) -> None:
        raws = list(Corpuses.iter_synthetic_profiles(50, seed=9))
        corpus = Corpuses.from_raw(raws)
        for np in corpus.vectorized_profiles:
            domain_bits = np.vector[4:]
            self.assertEqual(sum(domain_bits), 1.0,
                             msg=f"domain bits must sum to 1.0: {domain_bits}")

    def test_single_domain_corpus_no_collapse(self) -> None:
        # All profiles share the same domain — one-hot bits must stay 1.0/0.0
        raws = [
            Profile(200 + i, float(20 + i), float(40 + i), float(2 + i % 3),
                       "bachelor", "software")
            for i in range(5)
        ]
        corpus = Corpuses.from_raw(raws)
        for np in corpus.vectorized_profiles:
            domain_bits = np.vector[4:]
            self.assertEqual(domain_bits[0], 1.0)  # software
            self.assertTrue(all(v == 0.0 for v in domain_bits[1:]))

    def test_query_normalization_domain_aligned(self) -> None:
        raws = list(Corpuses.iter_synthetic_profiles(20, seed=3))
        corpus = Corpuses.from_raw(raws)
        for domain in DOMAIN_CATALOG:
            query = Profile(999, 30.0, 50.0, 4.0, "bachelor", domain)
            vec = corpus.normalize_query(query)
            self.assertEqual(len(vec), VECTOR_DIM)
            domain_bits = vec[4:]
            self.assertEqual(sum(domain_bits), 1.0)
            idx = DOMAIN_CATALOG.index(domain)
            self.assertEqual(domain_bits[idx], 1.0)


if __name__ == "__main__":
    unittest.main()
