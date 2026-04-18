"""Tests for heap top-k."""

import unittest

from services.helper import ValidationError
from services.search.topk import finalize_top_k, push_top_k, scan_top_k


class TestTopK(unittest.TestCase):
    def test_keeps_k_smallest(self) -> None:
        heap: list = []
        for pid, d in [(40, 3.0), (20, 1.0), (30, 2.0), (10, 0.5)]:
            push_top_k(heap, d, pid, k=2)
        got = finalize_top_k(heap)
        self.assertEqual(got, [(10, 0.5), (20, 1.0)])

    def test_tie_break_by_profile_id(self) -> None:
        heap: list = []
        push_top_k(heap, 1.0, 26, k=1)
        push_top_k(heap, 1.0, 10, k=1)
        got = finalize_top_k(heap)
        self.assertEqual(got, [(10, 1.0)])

    def test_scan_top_k(self) -> None:
        pairs = [(24, 10.0), (25, 2.0), (26, 5.0)]
        got = scan_top_k(pairs, k=2)
        self.assertEqual(got, [(25, 2.0), (26, 5.0)])

    def test_k_must_be_positive(self) -> None:
        with self.assertRaises(ValidationError):
            push_top_k([], 0.0, 1, k=0)


if __name__ == "__main__":
    unittest.main()
