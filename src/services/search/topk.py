"""Streaming top-k selection by (distance, profile_id) lexicographic order."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Iterable

from services.helper import ValidationError


@dataclass(frozen=True, slots=True, order=False)
class _WorstKey:
    """Min-heap key whose smallest element is the worst (largest) (distance, id)."""

    distance: float
    profile_id: str

    def __lt__(self, other: _WorstKey) -> bool:
        return (self.distance, self.profile_id) > (other.distance, other.profile_id)


def push_top_k(
    heap: list[_WorstKey],
    distance: float,
    profile_id: str,
    k: int,
) -> None:
    """Insert (distance, profile_id) into a structure keeping k best pairs.

    "Best" means smallest (distance, profile_id) in lexicographic order.

    Args:
        heap: Internal min-heap of ``_WorstKey`` entries (mutated in place).
        distance: Non-negative distance score.
        profile_id: Stable identifier for tie-breaking.
        k: Maximum number of hits to retain (must be >= 1).

    Raises:
        ValidationError: If k < 1.
    """
    if k < 1:
        raise ValidationError("k must be at least 1")
    cand = (distance, profile_id)
    if len(heap) < k:
        heapq.heappush(heap, _WorstKey(distance, profile_id))
        return
    worst = heap[0]
    if cand < (worst.distance, worst.profile_id):
        heapq.heapreplace(heap, _WorstKey(distance, profile_id))


def finalize_top_k(heap: list[_WorstKey]) -> list[tuple[str, float]]:
    """Sort heap contents as ascending (distance, profile_id).

    Args:
        heap: Heap populated by :func:`push_top_k`.

    Returns:
        List of ``(profile_id, distance)`` sorted best-first.
    """
    items = [(w.profile_id, w.distance) for w in heap]
    items.sort(key=lambda t: (t[1], t[0]))
    return items


def scan_top_k(
    pairs: Iterable[tuple[str, float]],
    k: int,
) -> list[tuple[str, float]]:
    """Collect top-k smallest (distance, id) from an iterable of (id, distance).

    Args:
        pairs: Iterable of ``(profile_id, distance)``.
        k: Number of neighbors.

    Returns:
        Sorted list of ``(profile_id, distance)``, length at most k.
    """
    h: list[_WorstKey] = []
    for pid, dist in pairs:
        push_top_k(h, dist, pid, k)
    return finalize_top_k(h)
