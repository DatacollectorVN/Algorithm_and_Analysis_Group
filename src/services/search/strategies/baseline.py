"""Exhaustive O(n) scan baseline for top-k similarity."""

from __future__ import annotations

from services.dataset import Corpuses
from services.helper import ValidationError
from services.search.distance import weighted_squared_distance
from services.search.strategies.base import SearchStrategy
from services.search.topk import TopKManager
from services.dto import TopKResult


class BaselineSearcher(SearchStrategy):
    """Full dataset scan with weighted distance and heap top-k."""

    __slots__ = ("_corpus",)

    def __init__(self, corpuses: Corpuses) -> None:
        super().__init__(corpuses)
        if not corpuses.vectorized_profiles:
            raise ValidationError("corpus must be non-empty for BaselineSearcher")
        self._corpus = list(corpuses.vectorized_profiles)

    def search(
        self,
        query_vector: tuple[float, ...],
        weights: tuple[float, ...],
        k: int,
    ) -> list[tuple[int, float]]:
        if k < 1:
            raise ValidationError("k must be at least 1")
        mgr: TopKManager = TopKManager()
        for p in self._corpus:
            d: float = weighted_squared_distance(query_vector, p.vector, weights)
            mgr.push(d, p.profile_id, k)
        res: list[tuple[int, float]] = mgr.finalize()
        profile_ids: list[int] = []
        distances: list[float] = []
        for id, dist in res:
            profile_ids.append(id)
            distances.append(dist)
        return TopKResult(profile_ids=tuple(profile_ids), distances=tuple(distances))


