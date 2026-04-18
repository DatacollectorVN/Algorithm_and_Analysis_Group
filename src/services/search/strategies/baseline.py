"""Exhaustive O(n) scan baseline for top-k similarity."""

from __future__ import annotations

from services.dataset import Corpuses
from services.helper import ValidationError
from services.search.distance import weighted_squared_distance
from services.search.strategies.base import SearchStrategy
from services.search.topk import TopKManager


class BaselineSearcher(SearchStrategy):
    """Full dataset scan with weighted distance and heap top-k."""

    __slots__ = ("_corpus",)

    def __init__(self, corpuses: Corpuses) -> None:
        super().__init__(corpuses)
        if not corpuses.normalized_profiles:
            raise ValidationError("corpus must be non-empty for BaselineSearcher")
        self._corpus = list(corpuses.normalized_profiles)

    def search(
        self,
        query_vector: tuple[float, float, float, float, float],
        weights: tuple[float, float, float, float, float],
        k: int,
    ) -> list[tuple[str, float]]:
        if k < 1:
            raise ValidationError("k must be at least 1")
        mgr = TopKManager()
        for p in self._corpus:
            d = weighted_squared_distance(query_vector, p.vector, weights)
            mgr.push(d, p.profile_id, k)
        return mgr.finalize()
