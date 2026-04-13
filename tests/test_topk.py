"""Tests for heap top-k."""

import unittest

from services.helper import ValidationError
from services.search.topk import finalize_top_k, push_top_k, scan_top_k


class TestTopK(unittest.TestCase):
    def test_keeps_k_smallest(self) -> None:
        heap: list = []
        for pid, d in [("a", 3.0), ("b", 1.0), ("c", 2.0), ("d", 0.5)]:
            push_top_k(heap, d, pid, k=2)
        got = finalize_top_k(heap)
        self.assertEqual(got, [("d", 0.5), ("b", 1.0)])

    def test_tie_break_by_profile_id(self) -> None:
        heap: list = []
        push_top_k(heap, 1.0, "z", k=1)
        push_top_k(heap, 1.0, "a", k=1)
        got = finalize_top_k(heap)
        self.assertEqual(got, [("a", 1.0)])

    def test_scan_top_k(self) -> None:
        pairs = [("x", 10.0), ("y", 2.0), ("z", 5.0)]
        got = scan_top_k(pairs, k=2)
        self.assertEqual(got, [("y", 2.0), ("z", 5.0)])

    def test_k_must_be_positive(self) -> None:
        with self.assertRaises(ValidationError):
            push_top_k([], 0.0, "a", k=0)


if __name__ == "__main__":
    unittest.main()
