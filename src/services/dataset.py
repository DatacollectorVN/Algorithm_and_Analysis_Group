"""Synthetic profile generation, categorical encoding, and Min–Max normalization."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Iterator, Sequence

from services.constants import DEGREE_CATALOG, DOMAIN_CATALOG, VECTOR_DIM
from services.dto import NormalizedProfile, RawProfile, ScalingStats
from services.helper import ValidationError, minmax_scalar


@dataclass(frozen=True, slots=True)
class Corpuses:
    """Min–Max–normalized corpus plus the :class:`ScalingStats` used to build it.

    Encoding, normalization, synthetic generation, and JSON load helpers live as
    class/static methods on this type; names starting with ``_`` are internal
    building blocks. Pass instances to :class:`BaselineSearcher` and
    :class:`KDTreeSearcher`.
    """

    normalized: tuple[NormalizedProfile, ...]
    stats: ScalingStats

    DEGREE_CATALOG: ClassVar[tuple[str, ...]] = DEGREE_CATALOG
    DOMAIN_CATALOG: ClassVar[tuple[str, ...]] = DOMAIN_CATALOG

    @staticmethod
    def _degree_to_rank(degree: str) -> float:
        """Map ``highest_degree`` string to ordinal rank as float."""
        try:
            return float(Corpuses.DEGREE_CATALOG.index(degree))
        except ValueError as exc:
            raise ValidationError(f"unknown highest_degree: {degree!r}") from exc

    @staticmethod
    def _domain_to_index(domain: str) -> float:
        """Map ``favourite_domain`` string to catalog index as float."""
        try:
            return float(Corpuses.DOMAIN_CATALOG.index(domain))
        except ValueError as exc:
            raise ValidationError(f"unknown favourite_domain: {domain!r}") from exc

    @staticmethod
    def _raw_to_prevector(raw: RawProfile) -> tuple[float, float, float, float, float]:
        """Encode raw profile to five numeric features before Min–Max."""
        return (
            float(raw.age),
            float(raw.monthly_income),
            Corpuses._degree_to_rank(raw.highest_degree),
            float(raw.daily_learning_hours),
            Corpuses._domain_to_index(raw.favourite_domain),
        )

    @staticmethod
    def _apply_minmax(
        pre: tuple[float, float, float, float, float],
        stats: ScalingStats,
    ) -> tuple[float, float, float, float, float]:
        """Scale one pre-vector using corpus Min–Max stats."""
        return (
            minmax_scalar(pre[0], stats.mins[0], stats.maxs[0]),
            minmax_scalar(pre[1], stats.mins[1], stats.maxs[1]),
            minmax_scalar(pre[2], stats.mins[2], stats.maxs[2]),
            minmax_scalar(pre[3], stats.mins[3], stats.maxs[3]),
            minmax_scalar(pre[4], stats.mins[4], stats.maxs[4]),
        )

    @staticmethod
    def _compute_scaling_stats(
        pre_vectors: Sequence[tuple[float, float, float, float, float]],
    ) -> ScalingStats:
        """Compute per-dimension min and max over a sequence of pre-vectors."""
        if not pre_vectors:
            raise ValidationError("cannot compute scaling stats on empty corpus")
        mins = list(pre_vectors[0])
        maxs = list(pre_vectors[0])
        for row in pre_vectors[1:]:
            for i in range(VECTOR_DIM):
                mins[i] = min(mins[i], row[i])
                maxs[i] = max(maxs[i], row[i])
        return ScalingStats(
            mins=(mins[0], mins[1], mins[2], mins[3], mins[4]),
            maxs=(maxs[0], maxs[1], maxs[2], maxs[3], maxs[4]),
        )

    @classmethod
    def iter_synthetic_profiles(
        cls, count: int, *, seed: int | None = None
    ) -> Iterator[RawProfile]:
        """Yield ``count`` synthetic profiles (stdlib ``random`` only)."""
        if count < 0:
            raise ValidationError("count must be non-negative")
        rng = random.Random(seed)
        for i in range(count):
            yield RawProfile(
                profile_id=f"synth-{i}",
                age=float(rng.randint(18, 70)),
                monthly_income=rng.uniform(5.0, 100.0),
                daily_learning_hours=rng.uniform(0.0, 8.0),
                highest_degree=rng.choice(cls.DEGREE_CATALOG),
                favourite_domain=rng.choice(cls.DOMAIN_CATALOG),
            )

    @classmethod
    def _build_normalized_pair(
        cls, raw_profiles: Sequence[RawProfile]
    ) -> tuple[list[NormalizedProfile], ScalingStats]:
        """Two-pass Min–Max: encode, stats, then normalize."""
        if not raw_profiles:
            raise ValidationError("corpus must be non-empty")
        pre = [cls._raw_to_prevector(r) for r in raw_profiles]
        stats = cls._compute_scaling_stats(pre)
        normalized: list[NormalizedProfile] = []
        for r, pv in zip(raw_profiles, pre, strict=True):
            normalized.append(NormalizedProfile(r.profile_id, cls._apply_minmax(pv, stats)))
        return normalized, stats

    @staticmethod
    def _normalize_query_raw(
        raw: RawProfile, stats: ScalingStats
    ) -> tuple[float, float, float, float, float]:
        """Normalize a query :class:`RawProfile` with corpus :class:`ScalingStats`."""
        return Corpuses._apply_minmax(Corpuses._raw_to_prevector(raw), stats)

    @classmethod
    def from_raw(cls, raw: Sequence[RawProfile]) -> Corpuses:
        """Build from raw profiles (two-pass Min–Max)."""
        normalized, stats = cls._build_normalized_pair(raw)
        return cls(tuple(normalized), stats)

    @classmethod
    def from_json_path(cls, corpus_path: str | Path) -> Corpuses:
        """Load corpus JSON from disk and return a :class:`Corpuses` bundle.

        Used by the ``search`` CLI path (not ``generate-corpus``).

        Args:
            corpus_path: Path to a UTF-8 JSON array of corpus records.

        Returns:
            Normalized corpus plus Min–Max stats for query alignment.

        Raises:
            ValidationError: If JSON shape or values are invalid.
        """
        from services.jsonio import load_corpus_json

        raw = load_corpus_json(corpus_path)
        return cls.from_raw(raw)

    @classmethod
    def from_normalized(
        cls,
        profiles: Sequence[NormalizedProfile],
        *,
        stats: ScalingStats | None = None,
    ) -> Corpuses:
        """Wrap an already-normalized corpus (e.g. tests). Uses ``[0,1]^5`` default stats if omitted."""
        if not profiles:
            raise ValidationError("corpus must be non-empty")
        if stats is None:
            stats = ScalingStats(
                mins=(0.0, 0.0, 0.0, 0.0, 0.0),
                maxs=(1.0, 1.0, 1.0, 1.0, 1.0),
            )
        return cls(tuple(profiles), stats)

    def normalize_query(self, raw: RawProfile) -> tuple[float, float, float, float, float]:
        """Normalize a query profile using this corpus's scaling stats."""
        return Corpuses._normalize_query_raw(raw, self.stats)

    def load_query(
        self, query_path: str | Path
    ) -> tuple[
        tuple[float, float, float, float, float], tuple[float, float, float, float, float], int
    ]:
        """Load query JSON and normalize the reference using this corpus's stats.

        Args:
            query_path: Path to query object (``reference``, ``weights``, ``k``).

        Returns:
            ``(normalized_query_vector, weights_tuple, k)``.
        """
        from services.jsonio import load_query_json

        ref_raw, weights, k = load_query_json(query_path)
        query_vec = self.normalize_query(ref_raw)
        return query_vec, weights, k


# --- Module-level aliases (same signatures as before; delegate to :class:`Corpuses`) ---


def degree_to_rank(degree: str) -> float:
    return Corpuses._degree_to_rank(degree)


def domain_to_index(domain: str) -> float:
    return Corpuses._domain_to_index(domain)


def raw_to_prevector(raw: RawProfile) -> tuple[float, float, float, float, float]:
    return Corpuses._raw_to_prevector(raw)


def apply_minmax(
    pre: tuple[float, float, float, float, float],
    stats: ScalingStats,
) -> tuple[float, float, float, float, float]:
    return Corpuses._apply_minmax(pre, stats)


def compute_scaling_stats(
    pre_vectors: Sequence[tuple[float, float, float, float, float]],
) -> ScalingStats:
    return Corpuses._compute_scaling_stats(pre_vectors)


def iter_synthetic_profiles(count: int, *, seed: int | None = None) -> Iterator[RawProfile]:
    yield from Corpuses.iter_synthetic_profiles(count, seed=seed)


def build_normalized_corpus(
    raw_profiles: Sequence[RawProfile],
) -> tuple[list[NormalizedProfile], ScalingStats]:
    return Corpuses._build_normalized_pair(raw_profiles)


def normalize_query_raw(
    raw: RawProfile, stats: ScalingStats
) -> tuple[float, float, float, float, float]:
    return Corpuses._normalize_query_raw(raw, stats)


def load_corpus_from_path(corpus_path: str | Path) -> Corpuses:
    """Load a corpus JSON file into a :class:`Corpuses` (CLI / library helper)."""
    return Corpuses.from_json_path(corpus_path)


def get_synthetic_corpus(corpus_path: str | Path) -> Corpuses:
    """Load corpus JSON for search (002 contract name); same as :meth:`Corpuses.from_json_path`."""
    return Corpuses.from_json_path(corpus_path)


def get_synthetic_query(
    query_path: str | Path,
    corpuses: Corpuses,
) -> tuple[tuple[float, float, float, float, float], tuple[float, float, float, float, float], int]:
    """Load query JSON and normalize reference (002 contract name); same as :meth:`Corpuses.load_query`."""
    return corpuses.load_query(query_path)
