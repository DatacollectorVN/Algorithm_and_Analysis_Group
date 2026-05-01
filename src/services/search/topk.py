"""Streaming top-k selection by (distance, profile_id) lexicographic order."""

from __future__ import annotations

from typing import Iterable

from services.search.storages import MinHeapStorage
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
