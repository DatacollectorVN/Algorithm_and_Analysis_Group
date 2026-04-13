"""Baseline vs KD-tree equivalence on synthetic corpora."""

import unittest

from services.dataset import Corpuses
from services.search.strategies.baseline import BaselineSearcher
from services.search.strategies.kdtree import KDTreeSearcher


class TestEquivalence(unittest.TestCase):
    def test_multiple_seeds(self) -> None:
        w = (1.0, 2.0, 0.5, 1.5, 1.0)
        for seed in (0, 1, 42, 99):
            raw = list(Corpuses.iter_synthetic_profiles(80, seed=seed))
            corpuses = Corpuses.from_raw(raw)
            base = BaselineSearcher(corpuses)
            tree = KDTreeSearcher(corpuses)
            q_raw = raw[0]
            qv = corpuses.normalize_query(q_raw)
            for k in (1, 5, 20, 50):
                hb = base.search(qv, w, k)
                hk = tree.search(qv, w, k)
                self.assertEqual(hb, hk, msg=f"seed={seed} k={k}")


if __name__ == "__main__":
    unittest.main()
