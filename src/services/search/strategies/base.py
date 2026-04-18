"""Abstract search strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from services.dataset import Corpuses
from services.dto.profiles import TopKResult
import time


class SearchStrategy(ABC):
    """Weighted top-k query over a corpus fixed at construction time."""

    def __init__(self, corpuses: Corpuses) -> None:
        """Subclasses call ``super().__init__(corpuses)`` and build index state."""
        _ = corpuses

    @abstractmethod
    def search(
        self,
        query_vector: tuple[float, ...],
        weights: tuple[float, ...],
        k: int,
    ) -> TopKResult:
        """Return up to ``k`` best neighbors as ``(profile_id, distance)``.

        Results are sorted by ascending distance, then ``profile_id``.
        """


def build_searcher(searcher_cls: type[SearchStrategy], corpuses: Corpuses) -> [SearchStrategy, float]:
    t0: float = time.perf_counter()
    instance: SearchStrategy = searcher_cls(corpuses)
    elapsed: float = time.perf_counter() - t0
    return instance, elapsed


def get_topk(
    searcher: SearchStrategy,
    query_vector: tuple[float, ...],
    weights: tuple[float, ...],
    k: int,
) -> [TopKResult, float]:
    """Run ``strategy.search`` and return ``(hits, elapsed_seconds)``."""
    t0: float = time.perf_counter()
    result: TopKResult = searcher.search(query_vector, weights, k)
    elapsed: float = time.perf_counter() - t0
    return result, elapsed
