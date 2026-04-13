"""Tests for KDTreeSearcher vs brute force."""

import random
import unittest

from services.dataset import Corpuses
from services.dto import NormalizedProfile
from services.search.distance import weighted_squared_distance
from services.search.strategies.kdtree import KDTreeSearcher


class TestKDTree(unittest.TestCase):
    def _brute(self, corpus: list[NormalizedProfile], q: tuple[float, ...], w: tuple[float, ...], k: int) -> list[tuple[str, float]]:
        scored = [(p.profile_id, weighted_squared_distance(q, p.vector, w)) for p in corpus]
        scored.sort(key=lambda t: (t[1], t[0]))
        return scored[:k]

    def test_matches_brute_small(self) -> None:
        rng = random.Random(0)
        corpus: list[NormalizedProfile] = []
        for i in range(30):
            v = tuple(rng.random() for _ in range(5))
            corpus.append(NormalizedProfile(f"id-{i}", v))
        w = (1.0, 0.5, 1.0, 0.25, 1.0)
        c = Corpuses.from_normalized(corpus)
        for _ in range(10):
            q = tuple(rng.random() for _ in range(5))
            for k in (1, 3, 7, 15):
                tree = KDTreeSearcher(c)
                got = tree.search(q, w, k)
                exp = self._brute(corpus, q, w, k)
                self.assertEqual(got, exp, msg=f"q={q} k={k}")

    def test_single_point(self) -> None:
        corpus = [NormalizedProfile("only", (0.2, 0.3, 0.4, 0.5, 0.6))]
        c = Corpuses.from_normalized(corpus)
        tree = KDTreeSearcher(c)
        w = (1.0, 1.0, 1.0, 1.0, 1.0)
        hits = tree.search((0.2, 0.3, 0.4, 0.5, 0.6), w, k=1)
        self.assertEqual(hits[0][1], 0.0)


if __name__ == "__main__":
    unittest.main()
