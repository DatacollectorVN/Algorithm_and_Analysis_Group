"""Tests for weighted distance."""

import unittest

from services.constants import VECTOR_DIM
from services.helper import ValidationError
from services.search.distance import weighted_squared_distance

# Convenience helpers for building 14-dim tuples
_ZEROS: tuple[float, ...] = (0.0,) * VECTOR_DIM
_ONES: tuple[float, ...] = (1.0,) * VECTOR_DIM
_UNIT_W: tuple[float, ...] = (1.0,) * VECTOR_DIM


def _vec(*vals: float) -> tuple[float, ...]:
    """Build a VECTOR_DIM tuple from leading values, padding with 0.0."""
    assert len(vals) <= VECTOR_DIM
    return vals + (0.0,) * (VECTOR_DIM - len(vals))


def _weights(*vals: float) -> tuple[float, ...]:
    """Build a VECTOR_DIM weight tuple from leading values, padding with 0.0."""
    assert len(vals) <= VECTOR_DIM
    return vals + (0.0,) * (VECTOR_DIM - len(vals))


class TestWeightedSquaredDistance(unittest.TestCase):
    def test_identical_zero(self) -> None:
        q = _ZEROS
        w = _UNIT_W
        self.assertEqual(weighted_squared_distance(q, q, w), 0.0)

    def test_weight_scales_dimension(self) -> None:
        q = _vec(1.0)
        p = _ZEROS
        w = _weights(2.0, 1.0)
        self.assertAlmostEqual(weighted_squared_distance(q, p, w), 2.0)

    def test_mixed_weights(self) -> None:
        q = _vec(1.0, 1.0)
        p = _ZEROS
        w = _weights(1.0, 3.0)
        self.assertAlmostEqual(weighted_squared_distance(q, p, w), 4.0)

    def test_rejects_negative_weight(self) -> None:
        with self.assertRaises(ValidationError):
            weighted_squared_distance(_ZEROS, _ZEROS, _ZEROS)

    def test_rejects_all_zero_weights(self) -> None:
        with self.assertRaises(ValidationError):
            weighted_squared_distance(_ZEROS, _ONES, _ZEROS)

    def test_rejects_nan(self) -> None:
        q = _vec(float("nan"))
        with self.assertRaises(ValidationError):
            weighted_squared_distance(q, _ZEROS, _UNIT_W)

    def test_rejects_wrong_length(self) -> None:
        short = (0.0, 0.0, 0.0, 0.0, 0.0)
        with self.assertRaises(ValidationError):
            weighted_squared_distance(short, short, short)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
