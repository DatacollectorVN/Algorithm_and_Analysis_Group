"""Tests for weighted distance."""

import unittest

from services.helper import ValidationError
from services.search.distance import weighted_squared_distance


class TestWeightedSquaredDistance(unittest.TestCase):
    def test_identical_zero(self) -> None:
        q = (0.5, 0.5, 0.5, 0.5, 0.5)
        w = (1.0, 1.0, 1.0, 1.0, 1.0)
        self.assertEqual(weighted_squared_distance(q, q, w), 0.0)

    def test_weight_scales_dimension(self) -> None:
        q = (1.0, 0.0, 0.0, 0.0, 0.0)
        p = (0.0, 0.0, 0.0, 0.0, 0.0)
        w = (2.0, 1.0, 1.0, 1.0, 1.0)
        self.assertAlmostEqual(weighted_squared_distance(q, p, w), 2.0)

    def test_mixed_weights(self) -> None:
        q = (1.0, 1.0, 0.0, 0.0, 0.0)
        p = (0.0, 0.0, 0.0, 0.0, 0.0)
        w = (1.0, 3.0, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(weighted_squared_distance(q, p, w), 4.0)

    def test_rejects_negative_weight(self) -> None:
        with self.assertRaises(ValidationError):
            weighted_squared_distance(
                (0.0, 0.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0, 0.0, 0.0),
            )

    def test_rejects_all_zero_weights(self) -> None:
        with self.assertRaises(ValidationError):
            weighted_squared_distance(
                (0.0, 0.0, 0.0, 0.0, 0.0),
                (1.0, 1.0, 1.0, 1.0, 1.0),
                (0.0, 0.0, 0.0, 0.0, 0.0),
            )

    def test_rejects_nan(self) -> None:
        with self.assertRaises(ValidationError):
            weighted_squared_distance(
                (float("nan"), 0.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0, 0.0, 0.0),
                (1.0, 1.0, 1.0, 1.0, 1.0),
            )


if __name__ == "__main__":
    unittest.main()
