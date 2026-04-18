"""Scale smoke: large synthetic corpus, both strategies complete."""

import os
import unittest

from services.constants import VECTOR_DIM
from services.dataset import Corpuses
from services.search.strategies.baseline import BaselineSearcher
from services.search.strategies.kdtree import KDTreeSearcher

_W: tuple[float, ...] = (1.0,) * VECTOR_DIM


class TestScaleSmoke(unittest.TestCase):
    def test_ten_thousand_profiles(self) -> None:
        n = 10_000
        raw = list(Corpuses.iter_synthetic_profiles(n, seed=7))
        corpuses = Corpuses.from_raw(raw)
        qv = corpuses.normalize_query(raw[100])
        k = 10
        b = BaselineSearcher(corpuses)
        t = KDTreeSearcher(corpuses)
        hb = b.search(qv, _W, k)
        hk = t.search(qv, _W, k)
        self.assertEqual(hb, hk)

    @unittest.skipUnless(os.environ.get("RUN_HEAVY") == "1", "set RUN_HEAVY=1 for 100k local run")
    def test_hundred_thousand_profiles(self) -> None:
        n = 100_000
        raw = list(Corpuses.iter_synthetic_profiles(n, seed=11))
        corpuses = Corpuses.from_raw(raw)
        qv = corpuses.normalize_query(raw[5000])
        k = 5
        b = BaselineSearcher(corpuses)
        t = KDTreeSearcher(corpuses)
        self.assertEqual(b.search(qv, _W, k), t.search(qv, _W, k))


if __name__ == "__main__":
    unittest.main()
