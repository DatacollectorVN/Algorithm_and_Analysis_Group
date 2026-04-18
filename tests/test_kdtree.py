"""Tests for KDTreeSearcher vs brute force."""

import random
import unittest

from services.constants import VECTOR_DIM
from services.dataset import Corpuses
from services.dto import VectorizedProfile
from services.search.distance import weighted_squared_distance
from services.search.strategies.kdtree import KDTreeSearcher


class TestKDTree(unittest.TestCase):
    def _brute(self, corpus: list[VectorizedProfile], q: tuple[float, ...], w: tuple[float, ...], k: int) -> list[tuple[int, float]]:
        scored = [(p.profile_id, weighted_squared_distance(q, p.vector, w)) for p in corpus]
        scored.sort(key=lambda t: (t[1], t[0]))
        return scored[:k]

    def test_matches_brute_small(self) -> None:
        rng = random.Random(0)
        corpus: list[VectorizedProfile] = []
        for i in range(30):
            v = tuple(rng.random() for _ in range(VECTOR_DIM))
            corpus.append(VectorizedProfile(i, v))
        w: tuple[float, ...] = tuple(
            [1.0, 0.5, 1.0, 0.25] + [1.0] * (VECTOR_DIM - 4)
        )
        c = Corpuses.from_normalized(corpus)
        for _ in range(10):
            q = tuple(rng.random() for _ in range(VECTOR_DIM))
            for k in (1, 3, 7, 15):
                tree = KDTreeSearcher(c)
                got = tree.search(q, w, k)
                exp = self._brute(corpus, q, w, k)
                self.assertEqual(got, exp, msg=f"q={q} k={k}")

    def test_single_point(self) -> None:
        v: tuple[float, ...] = tuple(0.1 * (i + 1) for i in range(VECTOR_DIM))
        corpus = [VectorizedProfile(1, v)]
        c = Corpuses.from_normalized(corpus)
        tree = KDTreeSearcher(c)
        w: tuple[float, ...] = (1.0,) * VECTOR_DIM
        hits = tree.search(v, w, k=1)
        self.assertEqual(hits[0][1], 0.0)


if __name__ == "__main__":
    unittest.main()
