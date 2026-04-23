"""Custom min-heap data structure for streaming top-k selection."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable


class TopKDataStructure(ABC):
    """Interface for top-k accumulators."""

    @abstractmethod
    def push(self, distance: float, profile_id: int, k: int) -> None: ...

    @abstractmethod
    def finalize(self) -> list[tuple[int, float]]: ...

    @property
    @abstractmethod
    def size(self) -> int: ...

    @abstractmethod
    def worst_distance(self) -> float: ...

    def scan(
        self, pairs: Iterable[tuple[int, float]], k: int
    ) -> list[tuple[int, float]]:
        for profile_id, distance in pairs:
            self.push(distance, profile_id, k)
        return self.finalize()


class MinHeapStorage(TopKDataStructure):
    """Top-k via a custom array-based binary min-heap.

    The heap root always holds the *worst* (largest) current candidate so that
    it can be replaced in O(log k) when a better entry arrives.
    """

    def __init__(self) -> None:
        self._data: list[tuple[float, int]] = []

    def _sift_up(self, i: int) -> None:
        data = self._data
        while i > 0:
            parent = (i - 1) >> 1
            if data[parent] > data[i]:
                break
            data[parent], data[i] = data[i], data[parent]
            i = parent

    def _sift_down(self, i: int) -> None:
        data = self._data
        n = len(data)
        while True:
            left, right = 2 * i + 1, 2 * i + 2
            worst = i
            if left < n and data[left] > data[worst]:
                worst = left
            if right < n and data[right] > data[worst]:
                worst = right
            if worst == i:
                break
            data[i], data[worst] = data[worst], data[i]
            i = worst

    def push(self, distance: float, profile_id: int, k: int) -> None:
        cand = (distance, profile_id)
        if len(self._data) < k:
            self._data.append(cand)
            self._sift_up(len(self._data) - 1)
        elif cand < self._data[0]:
            self._data[0] = cand
            self._sift_down(0)

    def finalize(self) -> list[tuple[int, float]]:
        result = [(pid, dist) for dist, pid in self._data]
        result.sort(key=lambda t: (t[1], t[0]))
        return result

    @property
    def size(self) -> int:
        return len(self._data)

    def worst_distance(self) -> float:
        return self._data[0][0] if self._data else math.inf
