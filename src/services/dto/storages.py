"""Custom data structures for streaming top-k selection by (distance, profile_id)."""

from __future__ import annotations

import bisect
import math
from abc import ABC, abstractmethod
from collections.abc import Iterable


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class TopKDataStructure(ABC):
    """Interface for data structures that maintain the k best (lowest-distance) entries.

    All concrete subclasses expose the same surface:
        push           — streaming insert with capacity k
        finalize       — return sorted (profile_id, distance) list
        scan           — convenience wrapper over push + finalize
        size           — number of entries currently held
        worst_distance — distance of the worst (largest) retained entry
    """

    @abstractmethod
    def push(self, distance: float, profile_id: int, k: int) -> None:
        """Insert a candidate; retain only the k best (smallest distance) entries."""

    @abstractmethod
    def finalize(self) -> list[tuple[int, float]]:
        """Return accumulated results sorted by (distance, profile_id) ascending."""

    @property
    @abstractmethod
    def size(self) -> int:
        """Number of entries currently held."""

    @abstractmethod
    def worst_distance(self) -> float:
        """Distance of the current worst (largest) retained entry, or inf if empty."""

    def scan(
        self,
        pairs: Iterable[tuple[int, float]],
        k: int,
    ) -> list[tuple[int, float]]:
        """Feed an iterable of (profile_id, distance) pairs and return top-k.

        Mirrors ``scan_top_k`` from services.search.topk.
        """
        for profile_id, distance in pairs:
            self.push(distance, profile_id, k)
        return self.finalize()


# ---------------------------------------------------------------------------
# 1. MinHeapStorage  —  custom array-based binary min-heap
# ---------------------------------------------------------------------------

class MinHeapStorage(TopKDataStructure):
    """Top-k via a custom min-heap whose minimum is the *worst* (largest) entry.

    Mirrors the _WorstKey / push_top_k / finalize_top_k logic in topk.py but
    implemented as a from-scratch binary heap (no heapq).
    """

    def __init__(self) -> None:
        # Each element: (distance, profile_id).
        # Comparison is *inverted*: larger (distance, profile_id) is "smaller" in
        # the heap so that heap[0] always holds the worst current candidate.
        self._data: list[tuple[float, int]] = []

    # ------------------------------------------------------------------
    # Internal heap mechanics
    # ------------------------------------------------------------------

    @staticmethod
    def _worse(a: tuple[float, int], b: tuple[float, int]) -> bool:
        """Return True if a is a worse (larger) entry than b."""
        return a > b

    def _sift_up(self, i: int) -> None:
        data = self._data
        while i > 0:
            parent = (i - 1) >> 1
            # Heap invariant: parent >= child (worst at root).
            if self._worse(data[parent], data[i]):
                break
            data[parent], data[i] = data[i], data[parent]
            i = parent

    def _sift_down(self, i: int) -> None:
        data = self._data
        n = len(data)
        while True:
            left = 2 * i + 1
            right = left + 1
            # Find the child with the *worst* (largest) key to maintain heap order.
            worst_child = i
            if left < n and self._worse(data[left], data[worst_child]):
                worst_child = left
            if right < n and self._worse(data[right], data[worst_child]):
                worst_child = right
            if worst_child == i:
                break
            data[i], data[worst_child] = data[worst_child], data[i]
            i = worst_child

    def _heap_push(self, item: tuple[float, int]) -> None:
        self._data.append(item)
        self._sift_up(len(self._data) - 1)

    def _heap_replace(self, item: tuple[float, int]) -> None:
        """Replace root with item (equivalent to heapreplace)."""
        self._data[0] = item
        self._sift_down(0)

    # ------------------------------------------------------------------
    # TopKDataStructure interface
    # ------------------------------------------------------------------

    def push(self, distance: float, profile_id: int, k: int) -> None:
        cand = (distance, profile_id)
        if len(self._data) < k:
            self._heap_push(cand)
            return
        worst = self._data[0]
        if cand < worst:
            self._heap_replace(cand)

    def finalize(self) -> list[tuple[int, float]]:
        result = [(pid, dist) for dist, pid in self._data]
        result.sort(key=lambda t: (t[1], t[0]))
        return result

    @property
    def size(self) -> int:
        return len(self._data)

    def worst_distance(self) -> float:
        return self._data[0][0] if self._data else math.inf


# ---------------------------------------------------------------------------
# 2. SortedListStorage  —  always-sorted list with binary-search insertion
# ---------------------------------------------------------------------------

class SortedListStorage(TopKDataStructure):
    """Top-k via a sorted list; insertion uses bisect for O(log k) search + O(k) shift."""

    def __init__(self) -> None:
        # Stored as (distance, profile_id) in ascending order so index 0 is best.
        self._data: list[tuple[float, int]] = []

    def push(self, distance: float, profile_id: int, k: int) -> None:
        item = (distance, profile_id)
        pos = bisect.bisect_left(self._data, item)
        if pos >= k:
            # New item is worse than every item already in the full list.
            return
        self._data.insert(pos, item)
        if len(self._data) > k:
            self._data.pop()  # Drop the worst (last) element.

    def finalize(self) -> list[tuple[int, float]]:
        return [(pid, dist) for dist, pid in self._data]

    @property
    def size(self) -> int:
        return len(self._data)

    def worst_distance(self) -> float:
        return self._data[-1][0] if self._data else math.inf


# ---------------------------------------------------------------------------
# 3. PriorityQueueStorage  —  enqueue/dequeue wrapper over MinHeapStorage
# ---------------------------------------------------------------------------

class PriorityQueueStorage(MinHeapStorage):
    """Top-k priority queue with explicit enqueue/dequeue_best API.

    Inherits the heap mechanics from MinHeapStorage; adds queue-oriented aliases
    so callers can reason about it as a priority queue rather than a heap.
    """

    def enqueue(self, distance: float, profile_id: int, k: int) -> None:
        """Alias for push — add a candidate to the priority queue."""
        self.push(distance, profile_id, k)

    def dequeue_best(self) -> tuple[int, float] | None:
        """Remove and return the best (lowest-distance) entry, or None if empty."""
        if not self._data:
            return None
        # The best entry is NOT at the root (root = worst). Find the minimum leaf.
        best = min(self._data)
        idx = self._data.index(best)
        last = self._data.pop()
        if idx < len(self._data):
            self._data[idx] = last
            self._sift_down(idx)
            self._sift_up(idx)
        dist, pid = best
        return (pid, dist)


# ---------------------------------------------------------------------------
# 4. SegmentTreeStorage  —  batch mode; segment tree for repeated min extraction
# ---------------------------------------------------------------------------

class SegmentTreeStorage(TopKDataStructure):
    """Top-k via a segment tree built at finalize time.

    push() accumulates candidates; finalize() builds a min-segment-tree and
    extracts the k smallest entries via repeated global-min queries in O(k log n).
    """

    _INF_ENTRY: tuple[float, int] = (math.inf, 0)

    def __init__(self) -> None:
        self._items: list[tuple[float, int]] = []  # (distance, profile_id)
        self._k: int = 1

    # ------------------------------------------------------------------
    # Segment tree helpers
    # ------------------------------------------------------------------

    def _build(self, arr: list[tuple[float, int]]) -> list[tuple[float, int]]:
        """Build a 1-indexed min-segment-tree over arr."""
        n = len(arr)
        size = 1
        while size < n:
            size <<= 1
        # tree[1..2*size-1]; leaves start at index `size`.
        tree: list[tuple[float, int]] = [self._INF_ENTRY] * (2 * size)
        for i, v in enumerate(arr):
            tree[size + i] = v
        for i in range(size - 1, 0, -1):
            tree[i] = min(tree[2 * i], tree[2 * i + 1])
        return tree

    @staticmethod
    def _leaf_count(tree: list[tuple[float, int]]) -> int:
        return len(tree) >> 1

    def _query_min_idx(self, tree: list[tuple[float, int]]) -> int:
        """Return the leaf index (0-based) of the global minimum."""
        i = 1
        size = self._leaf_count(tree)
        while i < size:
            i = 2 * i if tree[2 * i] <= tree[2 * i + 1] else 2 * i + 1
        return i - size

    def _mark_deleted(self, tree: list[tuple[float, int]], leaf_idx: int) -> None:
        """Set leaf to INF and propagate upwards to maintain tree invariant."""
        size = self._leaf_count(tree)
        i = size + leaf_idx
        tree[i] = self._INF_ENTRY
        i >>= 1
        while i >= 1:
            tree[i] = min(tree[2 * i], tree[2 * i + 1])
            i >>= 1

    # ------------------------------------------------------------------
    # TopKDataStructure interface
    # ------------------------------------------------------------------

    def push(self, distance: float, profile_id: int, k: int) -> None:
        self._k = k
        self._items.append((distance, profile_id))

    def finalize(self) -> list[tuple[int, float]]:
        if not self._items:
            return []
        k = min(self._k, len(self._items))
        tree = self._build(self._items)
        extracted: list[tuple[float, int]] = []
        for _ in range(k):
            if tree[1] == self._INF_ENTRY:
                break
            idx = self._query_min_idx(tree)
            extracted.append(self._items[idx])
            self._mark_deleted(tree, idx)
        extracted.sort()
        return [(pid, dist) for dist, pid in extracted]

    @property
    def size(self) -> int:
        return len(self._items)

    def worst_distance(self) -> float:
        # Batch mode: no streaming worst; return inf so pruning is never applied.
        return math.inf


# ---------------------------------------------------------------------------
# 5. QuickSelectStorage  —  batch mode; Quickselect for O(n) k-th smallest
# ---------------------------------------------------------------------------

class QuickSelectStorage(TopKDataStructure):
    """Top-k via Quickselect (Lomuto partition with median-of-three pivot).

    push() accumulates all candidates; finalize() partitions to find the k
    smallest in O(n) average time, then sorts only that subset.
    """

    def __init__(self) -> None:
        self._items: list[tuple[float, int]] = []
        self._k: int = 1

    # ------------------------------------------------------------------
    # Quickselect helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _median_of_three(
        arr: list[tuple[float, int]], lo: int, hi: int
    ) -> tuple[float, int]:
        mid = (lo + hi) >> 1
        a, b, c = arr[lo], arr[mid], arr[hi]
        if a <= b <= c or c <= b <= a:
            return b
        if b <= a <= c or c <= a <= b:
            return a
        return c

    @staticmethod
    def _partition(
        arr: list[tuple[float, int]], lo: int, hi: int, pivot: tuple[float, int]
    ) -> int:
        """Lomuto-style partition around pivot value; returns final pivot index."""
        pivot_idx = next(i for i in range(lo, hi + 1) if arr[i] == pivot)
        arr[pivot_idx], arr[hi] = arr[hi], arr[pivot_idx]
        store = lo
        for j in range(lo, hi):
            if arr[j] < pivot:
                arr[store], arr[j] = arr[j], arr[store]
                store += 1
        arr[store], arr[hi] = arr[hi], arr[store]
        return store

    def _quickselect(self, arr: list[tuple[float, int]], k: int) -> None:
        """Rearrange arr in-place so arr[:k] holds the k smallest elements."""
        lo, hi = 0, len(arr) - 1
        while lo < hi:
            pivot = self._median_of_three(arr, lo, hi)
            p = self._partition(arr, lo, hi, pivot)
            if p + 1 == k:
                return
            elif p + 1 < k:
                lo = p + 1
            else:
                hi = p - 1

    # ------------------------------------------------------------------
    # TopKDataStructure interface
    # ------------------------------------------------------------------

    def push(self, distance: float, profile_id: int, k: int) -> None:
        self._k = k
        self._items.append((distance, profile_id))

    def finalize(self) -> list[tuple[int, float]]:
        n = len(self._items)
        k = min(self._k, n)
        if n == 0:
            return []
        arr = list(self._items)
        if k < n:
            self._quickselect(arr, k)
        top = arr[:k]
        top.sort()
        return [(pid, dist) for dist, pid in top]

    @property
    def size(self) -> int:
        return len(self._items)

    def worst_distance(self) -> float:
        # Batch mode: no streaming worst; return inf so pruning is never applied.
        return math.inf
