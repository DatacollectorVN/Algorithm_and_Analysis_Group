"""Tests for BaselineSearcher."""

import unittest

from services.constants import VECTOR_DIM
from services.dataset import Corpuses
from services.dto import NormalizedProfile, RawProfile
from services.helper import ValidationError
from services.search.strategies.baseline import BaselineSearcher

_Z: tuple[float, ...] = (0.0,) * VECTOR_DIM
_H: tuple[float, ...] = (0.5,) * VECTOR_DIM
_O: tuple[float, ...] = (1.0,) * VECTOR_DIM
_W: tuple[float, ...] = (1.0,) * VECTOR_DIM


class TestBaseline(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = [
            NormalizedProfile("a", _Z),
            NormalizedProfile("b", _O),
            NormalizedProfile("c", _H),
        ]
        self.w = _W

    def test_k_larger_than_n(self) -> None:
        c = Corpuses.from_normalized(self.corpus)
        s = BaselineSearcher(c)
        hits = s.search(_Z, self.w, k=100)
        self.assertEqual(len(hits), 3)

    def test_k_one(self) -> None:
        c = Corpuses.from_normalized(self.corpus)
        s = BaselineSearcher(c)
        hits = s.search(_Z, self.w, k=1)
        self.assertEqual(hits[0][0], "a")
        self.assertEqual(hits[0][1], 0.0)

    def test_tie_distance_prefers_lexicographic_id(self) -> None:
        pts = [
            NormalizedProfile("m", _Z),
            NormalizedProfile("n", _Z),
        ]
        c = Corpuses.from_normalized(pts)
        s = BaselineSearcher(c)
        hits = s.search(_Z, self.w, k=1)
        self.assertEqual(hits[0][0], "m")

    def test_invalid_k(self) -> None:
        c = Corpuses.from_normalized(self.corpus)
        s = BaselineSearcher(c)
        with self.assertRaises(ValidationError):
            s.search(_Z, self.w, k=0)

    def test_from_raw_pipeline(self) -> None:
        raw = [
            RawProfile("p1", 20.0, 10.0, 1.0, "bachelor", "software"),
            RawProfile("p2", 40.0, 20.0, 2.0, "master", "finance"),
        ]
        corpuses = Corpuses.from_raw(raw)
        s = BaselineSearcher(corpuses)
        q = corpuses.normalize_query(raw[0])
        hits = s.search(q, _W, k=2)
        self.assertEqual(len(hits), 2)


if __name__ == "__main__":
    unittest.main()
