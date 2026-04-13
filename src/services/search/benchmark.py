"""Wall-clock timing helpers for search and index build (stdlib ``time`` only)."""

from __future__ import annotations

import time
from typing import TypeVar

from services.dataset import Corpuses
from services.search.strategies.base import SearchStrategy

S = TypeVar("S", bound=SearchStrategy)


def timed_searcher_construct(searcher_cls: type[S], corpuses: Corpuses) -> tuple[S, float]:
    """Construct ``searcher_cls(corpuses)`` and return ``(instance, elapsed_seconds)``."""
    t0 = time.perf_counter()
    instance = searcher_cls(corpuses)
    elapsed = time.perf_counter() - t0
    return instance, elapsed


def timed_search(
    strategy: SearchStrategy,
    query_vector: tuple[float, float, float, float, float],
    weights: tuple[float, float, float, float, float],
    k: int,
) -> tuple[list[tuple[str, float]], float]:
    """Run ``strategy.search`` and return ``(hits, elapsed_seconds)``."""
    t0 = time.perf_counter()
    hits = strategy.search(query_vector, weights, k)
    elapsed = time.perf_counter() - t0
    return hits, elapsed
