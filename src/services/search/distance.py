"""Weighted squared-distance between normalized 14-vectors."""

from __future__ import annotations

import math

from services.constants import VECTOR_DIM
from services.helper import ValidationError


def weighted_squared_distance(
    query: tuple[float, ...],
    point: tuple[float, ...],
    weights: tuple[float, ...],
) -> float:
    """Compute sum_i w_i * (q_i - p_i)^2.

    Args:
        query: Normalized query vector (``VECTOR_DIM`` dimensions).
        point: Normalized corpus point (``VECTOR_DIM`` dimensions).
        weights: Non-negative per-dimension weights; at least one must be > 0.

    Returns:
        Non-negative weighted squared distance.

    Raises:
        ValidationError: If vectors are wrong length, weights invalid, or values
            are not finite.
    """
    if len(query) != VECTOR_DIM or len(point) != VECTOR_DIM or len(weights) != VECTOR_DIM:
        raise ValidationError(
            f"query, point, and weights must have length {VECTOR_DIM}"
        )
    _validate_weights(weights)
    total = 0.0
    for i in range(VECTOR_DIM):
        qi, pi, wi = query[i], point[i], weights[i]
        if not (math.isfinite(qi) and math.isfinite(pi)):
            raise ValidationError("query and point coordinates must be finite")
        diff = qi - pi
        total += wi * diff * diff
    if not math.isfinite(total):
        raise ValidationError("distance overflowed to non-finite value")
    return total


def _validate_weights(weights: tuple[float, ...]) -> None:
    positive = False
    for w in weights:
        if not math.isfinite(w):
            raise ValidationError("weights must be finite")
        if w < 0:
            raise ValidationError("weights must be non-negative")
        if w > 0:
            positive = True
    if not positive:
        raise ValidationError("at least one weight must be positive")
