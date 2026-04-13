"""Tests for validation paths."""

import unittest

from services.helper import ValidationError
from services.search.distance import weighted_squared_distance


class TestExceptions(unittest.TestCase):
    def test_non_finite_weight(self) -> None:
        with self.assertRaises(ValidationError):
            weighted_squared_distance(
                (0.0, 0.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0, 0.0, 0.0),
                (1.0, float("inf"), 0.0, 0.0, 0.0),
            )


if __name__ == "__main__":
    unittest.main()
