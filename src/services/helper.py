"""Shared numeric and geometry helpers (pure functions, no I/O) and domain exceptions."""

from __future__ import annotations

import math

from services.constants import HITS_EQUAL_ABS_TOL, VECTOR_DIM
from services.dto import ProfileVector


def minmax_scalar(x: float, lo: float, hi: float) -> float:
    """Map ``x`` into ``[0, 1]`` using ``[lo, hi]``; constant dimension → ``0.0``."""
    if hi == lo:
        return 0.0
    return (x - lo) / (hi - lo)


def bbox_of_point(v: ProfileVector) -> tuple[ProfileVector, ProfileVector]:
    """Degenerate axis-aligned box for a single point."""
    return v, v


def union_bbox(
    lo1: ProfileVector,
    hi1: ProfileVector,
    lo2: ProfileVector,
    hi2: ProfileVector,
) -> tuple[ProfileVector, ProfileVector]:
    """Merge two axis-aligned boxes (component-wise min/max)."""
    lo: ProfileVector = tuple(min(lo1[i], lo2[i]) for i in range(VECTOR_DIM))  # type: ignore[assignment]
    hi: ProfileVector = tuple(max(hi1[i], hi2[i]) for i in range(VECTOR_DIM))  # type: ignore[assignment]
    return lo, hi


def weighted_sq_dist_query_to_box(
    query: ProfileVector,
    weights: ProfileVector,
    lo: ProfileVector,
    hi: ProfileVector,
) -> float:  # ProfileVector is tuple[float, ...] — length enforced by VECTOR_DIM loop
    """Lower bound on Σ w_i (q_i - p_i)² for any ``p`` inside ``[lo, hi]``."""
    total = 0.0
    for i in range(VECTOR_DIM):
        qi = query[i]
        if qi < lo[i]:
            t = qi - lo[i]
        elif qi > hi[i]:
            t = qi - hi[i]
        else:
            t = 0.0
        total += weights[i] * t * t
    return total


def hits_equal(
    a: list[tuple[int, float]],
    b: list[tuple[int, float]],
    *,
    tol: float = HITS_EQUAL_ABS_TOL,
) -> bool:
    """Return True if hit lists match (same ids order, distances within ``tol``)."""
    if len(a) != len(b):
        return False
    for (ida, da), (idb, db) in zip(a, b, strict=True):
        if ida != idb:
            return False
        if not math.isclose(da, db, rel_tol=0.0, abs_tol=tol):
            return False
    return True


class LookalikeSearchError(Exception):
    """Base class for all recoverable errors in this package."""

    pass


class ValidationError(LookalikeSearchError):
    """Raised when inputs, corpus records, or query payloads are invalid."""

    pass