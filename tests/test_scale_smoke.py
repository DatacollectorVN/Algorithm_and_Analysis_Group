"""Scale smoke: large synthetic corpus, both strategies complete."""

import os
import unittest

from services.dataset import Corpuses
from services.search.strategies.baseline import BaselineSearcher
from services.search.strategies.kdtree import KDTreeSearcher


class TestScaleSmoke(unittest.TestCase):
    def test_ten_thousand_profiles(self) -> None:
        n = 10_000
        raw = list(Corpuses.iter_synthetic_profiles(n, seed=7))
        corpuses = Corpuses.from_raw(raw)
        w = (1.0, 1.0, 1.0, 1.0, 1.0)
        qv = corpuses.normalize_query(raw[100])
        k = 10
        b = BaselineSearcher(corpuses)
        t = KDTreeSearcher(corpuses)
        hb = b.search(qv, w, k)
        hk = t.search(qv, w, k)
        self.assertEqual(hb, hk)

    @unittest.skipUnless(os.environ.get("RUN_HEAVY") == "1", "set RUN_HEAVY=1 for 100k local run")
    def test_hundred_thousand_profiles(self) -> None:
        n = 100_000
        raw = list(Corpuses.iter_synthetic_profiles(n, seed=11))
        corpuses = Corpuses.from_raw(raw)
        w = (1.0, 1.0, 1.0, 1.0, 1.0)
        qv = corpuses.normalize_query(raw[5000])
        k = 5
        b = BaselineSearcher(corpuses)
        t = KDTreeSearcher(corpuses)
        self.assertEqual(b.search(qv, w, k), t.search(qv, w, k))


if __name__ == "__main__":
    unittest.main()
