"""Tests for BaselineSearcher."""

import unittest

from services.dataset import Corpuses
from services.dto import NormalizedProfile, RawProfile
from services.helper import ValidationError
from services.search.strategies.baseline import BaselineSearcher


class TestBaseline(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = [
            NormalizedProfile("a", (0.0, 0.0, 0.0, 0.0, 0.0)),
            NormalizedProfile("b", (1.0, 0.0, 0.0, 0.0, 0.0)),
            NormalizedProfile("c", (0.5, 0.5, 0.5, 0.5, 0.5)),
        ]
        self.w = (1.0, 1.0, 1.0, 1.0, 1.0)

    def test_k_larger_than_n(self) -> None:
        c = Corpuses.from_normalized(self.corpus)
        s = BaselineSearcher(c)
        q = (0.0, 0.0, 0.0, 0.0, 0.0)
        hits = s.search(q, self.w, k=100)
        self.assertEqual(len(hits), 3)

    def test_k_one(self) -> None:
        c = Corpuses.from_normalized(self.corpus)
        s = BaselineSearcher(c)
        q = (0.0, 0.0, 0.0, 0.0, 0.0)
        hits = s.search(q, self.w, k=1)
        self.assertEqual(hits[0][0], "a")
        self.assertEqual(hits[0][1], 0.0)

    def test_tie_distance_prefers_lexicographic_id(self) -> None:
        pts = [
            NormalizedProfile("m", (0.0, 0.0, 0.0, 0.0, 0.0)),
            NormalizedProfile("n", (0.0, 0.0, 0.0, 0.0, 0.0)),
        ]
        c = Corpuses.from_normalized(pts)
        s = BaselineSearcher(c)
        hits = s.search((0.0, 0.0, 0.0, 0.0, 0.0), self.w, k=1)
        self.assertEqual(hits[0][0], "m")

    def test_invalid_k(self) -> None:
        c = Corpuses.from_normalized(self.corpus)
        s = BaselineSearcher(c)
        with self.assertRaises(ValidationError):
            s.search((0.0, 0.0, 0.0, 0.0, 0.0), self.w, k=0)

    def test_from_raw_pipeline(self) -> None:
        raw = [
            RawProfile("p1", 20.0, 10.0, 1.0, "bachelor", "software"),
            RawProfile("p2", 40.0, 20.0, 2.0, "master", "finance"),
        ]
        corpuses = Corpuses.from_raw(raw)
        s = BaselineSearcher(corpuses)
        q = (0.5, 0.5, 0.5, 0.5, 0.5)
        hits = s.search(q, (1.0, 1.0, 1.0, 1.0, 1.0), k=2)
        self.assertEqual(len(hits), 2)


if __name__ == "__main__":
    unittest.main()
