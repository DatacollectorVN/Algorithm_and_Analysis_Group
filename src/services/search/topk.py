"""Streaming top-k selection by (distance, profile_id) lexicographic order."""

from __future__ import annotations

import heapq
import os
from dataclasses import dataclass
from typing import Iterable

from services.dto.storages import (
    MinHeapStorage,
    PriorityQueueStorage,
    QuickSelectStorage,
    SegmentTreeStorage,
    SortedListStorage,
    TopKDataStructure,
)
from services.helper import ValidationError

# Environment variable that selects the backing storage for TopKManager.
TOPK_STORAGE_ENV = "TOPK_STORAGE"

_STORAGE_REGISTRY: dict[str, type[TopKDataStructure]] = {
    "heap": MinHeapStorage,
    "sorted_list": SortedListStorage,
    "priority_queue": PriorityQueueStorage,
    "segment_tree": SegmentTreeStorage,
    "quickselect": QuickSelectStorage,
}


class TopKManager:
    """Top-k accumulator whose backend is selected via the TOPK_STORAGE env var.

    Set ``TOPK_STORAGE`` to one of:
        heap            — custom array min-heap  (default)
        sorted_list     — always-sorted list with bisect insertion
        priority_queue  — priority-queue wrapper over the heap
        segment_tree    — batch segment-tree extraction
        quickselect     — batch Lomuto quickselect

    Example::

        os.environ["TOPK_STORAGE"] = "sorted_list"
        mgr = TopKManager()
        mgr.push(1.5, "alice", k=3)
        results = mgr.finalize()
    """

    def __init__(self) -> None:
        key = os.environ.get(TOPK_STORAGE_ENV, "heap").lower()
        cls = _STORAGE_REGISTRY.get(key)
        if cls is None:
            valid = list(_STORAGE_REGISTRY)
            raise ValidationError(
                f"Unknown {TOPK_STORAGE_ENV}={key!r}. Valid values: {valid}"
            )
        self._storage: TopKDataStructure = cls()

    # ------------------------------------------------------------------
    # Core interface — mirrors push_top_k / finalize_top_k / scan_top_k
    # ------------------------------------------------------------------

    def push(self, distance: float, profile_id: str, k: int) -> None:
        """Insert a candidate; retain only the k best (smallest distance) entries."""
        if k < 1:
            raise ValidationError("k must be at least 1")
        self._storage.push(distance, profile_id, k)

    def finalize(self) -> list[tuple[str, float]]:
        """Return results sorted by (distance, profile_id) ascending."""
        return self._storage.finalize()

    def scan(
        self,
        pairs: Iterable[tuple[str, float]],
        k: int,
    ) -> list[tuple[str, float]]:
        """Feed an iterable of (profile_id, distance) pairs and return top-k."""
        return self._storage.scan(pairs, k)

    # ------------------------------------------------------------------
    # Structural accessors used by tree-based search strategies
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Number of entries currently held."""
        return self._storage.size

    def worst_distance(self) -> float:
        """Distance of the worst retained entry; inf if empty or batch-mode storage."""
        return self._storage.worst_distance()


# ---------------------------------------------------------------------------
# Legacy functional API — kept for reference; strategies now use TopKManager
# ---------------------------------------------------------------------------

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
    items = [(w.profile_id, w.distance) for w in heap]
    items.sort(key=lambda t: (t[1], t[0]))
    return items


def scan_top_k(
    pairs: Iterable[tuple[str, float]],
    k: int,
) -> list[tuple[str, float]]:
    h: list[_WorstKey] = []
    for pid, dist in pairs:
        push_top_k(h, dist, pid, k)
    return finalize_top_k(h)
