"""Streaming top-k selection by (distance, profile_id) lexicographic order."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Iterable

from services.dto.storages import MinHeapStorage
from services.helper import ValidationError


class TopKManager:
    """Top-k accumulator backed by MinHeapStorage."""

    def __init__(self) -> None:
        self._storage = MinHeapStorage()

    def push(self, distance: float, profile_id: int, k: int) -> None:
        if k < 1:
            raise ValidationError("k must be at least 1")
        self._storage.push(distance, profile_id, k)

    def finalize(self) -> list[tuple[int, float]]:
        return self._storage.finalize()

    def scan(self, pairs: Iterable[tuple[int, float]], k: int) -> list[tuple[int, float]]:
        return self._storage.scan(pairs, k)

    @property
    def size(self) -> int:
        return self._storage.size

    def worst_distance(self) -> float:
        return self._storage.worst_distance()


# ---------------------------------------------------------------------------
# Legacy functional API — used by tests and strategies
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True, order=False)
class _WorstKey:
    distance: float
    profile_id: int

    def __lt__(self, other: _WorstKey) -> bool:
        return (self.distance, self.profile_id) > (other.distance, other.profile_id)


def push_top_k(heap: list[_WorstKey], distance: float, profile_id: int, k: int) -> None:
    if k < 1:
        raise ValidationError("k must be at least 1")
    cand = (distance, profile_id)
    if len(heap) < k:
        heapq.heappush(heap, _WorstKey(distance, profile_id))
        return
    worst = heap[0]
    if cand < (worst.distance, worst.profile_id):
        heapq.heapreplace(heap, _WorstKey(distance, profile_id))


def finalize_top_k(heap: list[_WorstKey]) -> list[tuple[int, float]]:
    items = [(w.profile_id, w.distance) for w in heap]
    items.sort(key=lambda t: (t[1], t[0]))
    return items


def scan_top_k(pairs: Iterable[tuple[int, float]], k: int) -> list[tuple[int, float]]:
    h: list[_WorstKey] = []
    for pid, dist in pairs:
        push_top_k(h, dist, pid, k)
    return finalize_top_k(h)
