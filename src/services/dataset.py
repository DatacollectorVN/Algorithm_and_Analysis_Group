"""Synthetic profile generation, categorical encoding, and Min–Max normalization."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Iterator, Sequence

from services.constants import DEGREE_CATALOG, DOMAIN_CATALOG, VECTOR_DIM
from services.dto import Profile, QProfile, ScalingStats, VectorizedProfile, VectorizedQueryProfile
from services.helper import ValidationError, minmax_scalar
from services.jsonio import load_query_json


@dataclass(frozen=True, slots=True)
class Corpuses:
    """Min–Max–normalized corpus and the :class:`ScalingStats` used to build it.

    Encoding, scaling, synthetic generation, and JSON-backed construction are exposed
    as static or class methods on this type. Pass instances to
    :class:`BaselineSearcher` and :class:`KDTreeSearcher`.
    """

    vectorized_profiles: tuple[VectorizedProfile, ...]
    stats: ScalingStats
    raw_profiles: tuple[Profile, ...]

    DEGREE_CATALOG: ClassVar[tuple[str, ...]] = DEGREE_CATALOG
    DOMAIN_CATALOG: ClassVar[tuple[str, ...]] = DOMAIN_CATALOG

    @staticmethod
    def degree_to_rank(degree: str) -> float:
        """Map a catalog ``highest_degree`` string to an ordinal rank (float).

        Args:
            degree: Value from :attr:`DEGREE_CATALOG`.

        Returns:
            Index of ``degree`` in the catalog, as a float.

        Raises:
            ValidationError: If ``degree`` is not in the catalog.
        """
        try:
            return float(Corpuses.DEGREE_CATALOG.index(degree))
        except ValueError as exc:
            raise ValidationError(f"unknown highest_degree: {degree!r}") from exc

    @staticmethod
    def domain_to_onehot(domain: str) -> tuple[float, ...]:
        """Map a catalog ``favourite_domain`` string to a one-hot float tuple.

        The returned tuple has one element per entry in :attr:`DOMAIN_CATALOG`.
        The element at the catalog index of ``domain`` is ``1.0``; all others
        are ``0.0``.

        Args:
            domain: Value from :attr:`DOMAIN_CATALOG`.

        Returns:
            Tuple of ``len(DOMAIN_CATALOG)`` floats with exactly one ``1.0``.

        Raises:
            ValidationError: If ``domain`` is not in the catalog.
        """
        try:
            idx = Corpuses.DOMAIN_CATALOG.index(domain)
        except ValueError as exc:
            raise ValidationError(f"unknown favourite_domain: {domain!r}") from exc
        return tuple(1.0 if i == idx else 0.0 for i in range(len(Corpuses.DOMAIN_CATALOG)))

    @staticmethod
    def raw_to_prevector(raw: Profile | QProfile) -> tuple[float, ...]:
        """Encode a raw profile to 14 numeric features before Min–Max scaling.

        Layout: ``(age, income, degree_rank, learning_hours, d0, d1, …, d9)``
        where ``d0``–``d9`` are one-hot bits for ``favourite_domain``.

        Args:
            raw: Corpus :class:`Profile` or query :class:`QProfile` (no ``profile_id`` required).

        Returns:
            14-float tuple with numeric features followed by domain one-hot bits.

        Raises:
            ValidationError: If a categorical field is not in its catalog.
        """
        return (
            float(raw.age),
            float(raw.monthly_income),
            Corpuses.degree_to_rank(raw.highest_degree),
            float(raw.daily_learning_hours),
            *Corpuses.domain_to_onehot(raw.favourite_domain),
        )

    @staticmethod
    def apply_minmax(
        pre: tuple[float, ...],
        stats: ScalingStats,
    ) -> tuple[float, ...]:
        """Min–Max scale the numeric dimensions of a pre-vector.

        Indices 0–3 (age, income, degree_rank, learning_hours) are scaled with
        ``minmax_scalar``. Indices 4 onward (one-hot domain bits) are copied
        through unchanged because they are already bounded to ``{0.0, 1.0}``.

        Args:
            pre: 14-float feature tuple before scaling.
            stats: Per-dimension min and max from :meth:`compute_scaling_stats`.

        Returns:
            14-float scaled tuple.
        """
        numeric = tuple(
            minmax_scalar(pre[i], stats.mins[i], stats.maxs[i]) for i in range(4)
        )
        domain_bits = pre[4:]
        return numeric + domain_bits

    @staticmethod
    def compute_scaling_stats(
        pre_vectors: Sequence[tuple[float, ...]],
    ) -> ScalingStats:
        """Compute per-dimension min and max over pre-vectors.

        Args:
            pre_vectors: Non-empty sequence of 14-float rows.

        Returns:
            Bundled min/max tuples (14 dimensions).

        Raises:
            ValidationError: If ``pre_vectors`` is empty.
        """
        if not pre_vectors:
            raise ValidationError("cannot compute scaling stats on empty corpus")
        mins = list(pre_vectors[0])
        maxs = list(pre_vectors[0])
        for row in pre_vectors[1:]:
            for i in range(VECTOR_DIM):
                mins[i] = min(mins[i], row[i])
                maxs[i] = max(maxs[i], row[i])
        return ScalingStats(
            mins=tuple(mins),
            maxs=tuple(maxs),
        )

    @classmethod
    def iter_synthetic_profiles(
        cls, count: int, *, seed: int | None = None
    ) -> Iterator[Profile]:
        """Yield ``count`` synthetic profiles using only ``random``.

        Args:
            count: Number of profiles; must be non-negative.
            seed: Optional RNG seed for reproducibility.

        Yields:
            :class:`Profile` instances whose ``profile_id`` runs from ``1`` to ``count``
            inclusive.

        Raises:
            ValidationError: If ``count`` is negative.
        """
        if count < 0:
            raise ValidationError("count must be non-negative")
        rng: random.Random = random.Random(seed)
        for i in range(count):
            yield Profile(
                profile_id=i + 1,
                age=float(rng.randint(18, 70)),
                monthly_income=rng.uniform(5.0, 100.0),
                daily_learning_hours=rng.uniform(0.0, 8.0),
                highest_degree=rng.choice(cls.DEGREE_CATALOG),
                favourite_domain=rng.choice(cls.DOMAIN_CATALOG),
            )

    @classmethod
    def build_normalized_corpus(
        cls, raw_profiles: Sequence[Profile]
    ) -> tuple[list[VectorizedProfile], ScalingStats]:
        """Two-pass Min–Max: encode, compute stats, then normalize each row.

        Args:
            raw_profiles: Non-empty sequence of raw profiles.

        Returns:
            ``(vectorized_profiles, scaling_stats)``.

        Raises:
            ValidationError: If ``raw_profiles`` is empty or encoding fails.
        """
        if not raw_profiles:
            raise ValidationError("corpus must be non-empty")
        pre: list[tuple[float, float, float, float, float]] = [
            cls.raw_to_prevector(r) for r in raw_profiles
        ]
        stats: ScalingStats = cls.compute_scaling_stats(pre)
        normalized: list[VectorizedProfile] = []
        for r, pv in zip(raw_profiles, pre, strict=True):
            normalized.append(VectorizedProfile(r.profile_id, cls.apply_minmax(pv, stats)))
        return normalized, stats

    @staticmethod
    def normalize_query_raw(
        raw: Profile | QProfile, stats: ScalingStats
    ) -> tuple[float, ...]:
        """Normalize a query profile with given :class:`ScalingStats`.

        Args:
            raw: Query reference (:class:`Profile` or :class:`QProfile`).
            stats: Scaling bounds from the corpus (e.g. ``corpuses.stats``).

        Returns:
            14-dimensional normalized query vector.

        Raises:
            ValidationError: If encoding fails for ``raw``.
        """
        return Corpuses.apply_minmax(Corpuses.raw_to_prevector(raw), stats)

    @classmethod
    def from_raw(cls, raw: Sequence[Profile]) -> Corpuses:
        """Build a corpus bundle from raw profiles (two-pass Min–Max).

        Args:
            raw: Non-empty sequence of raw profiles.

        Returns:
            Frozen bundle of vectorized profiles and stats.

        Raises:
            ValidationError: If ``raw`` is empty or invalid.
        """
        normalized: list[VectorizedProfile]
        stats: ScalingStats
        normalized, stats = cls.build_normalized_corpus(raw)
        return cls(vectorized_profiles=tuple(normalized), stats=stats, raw_profiles=tuple(raw))

    @classmethod
    def from_json_path(cls, corpus_path: str | Path) -> Corpuses:
        """Load corpus JSON from disk and return a :class:`Corpuses` bundle.

        Used by the ``search`` CLI path (not ``build``).

        Args:
            corpus_path: Path to a UTF-8 JSON array of corpus records.

        Returns:
            Normalized corpus plus Min–Max stats for query alignment.

        Raises:
            ValidationError: If JSON shape or values are invalid.
        """
        from services.jsonio import load_corpus_json

        raw: list[Profile] = load_corpus_json(corpus_path)
        return cls.from_raw(raw)

    @classmethod
    def from_normalized(
        cls,
        profiles: Sequence[VectorizedProfile],
        *,
        stats: ScalingStats | None = None,
    ) -> Corpuses:
        """Wrap an already-normalized corpus (e.g. tests).

        Args:
            profiles: Non-empty vectorized profiles.
            stats: Optional stats; defaults to ``[0,1]^5`` min/max if omitted.

        Returns:
            Corpus bundle.

        Raises:
            ValidationError: If ``profiles`` is empty.
        """
        if not profiles:
            raise ValidationError("corpus must be non-empty")
        if stats is None:
            stats = ScalingStats(
                mins=tuple(0.0 for _ in range(VECTOR_DIM)),
                maxs=tuple(1.0 for _ in range(VECTOR_DIM)),
            )
        return cls(vectorized_profiles=tuple(profiles), stats=stats, raw_profiles=tuple(profiles)  )

    def normalize_query(self, raw: Profile | QProfile) -> tuple[float, ...]:
        """Normalize a query profile using this corpus's scaling stats.

        Args:
            raw: Query reference (:class:`Profile` or :class:`QProfile`).

        Returns:
            Normalized 14-vector aligned to :attr:`stats`.
        """
        return Corpuses.normalize_query_raw(raw, self.stats)

    def get_profile(self, profile_id: int) -> Profile:
        """Get a raw profile by ``profile_id``."""
        return self.raw_profiles[profile_id - 1]
    
    def get_profiles(self, profile_ids: Sequence[int]) -> tuple[Profile, ...]:
        """Get raw profiles by ``profile_ids``."""
        return tuple(self.raw_profiles[pid - 1] for pid in profile_ids)

    def build_vectorized_query(self, query_path: str | Path) -> VectorizedQueryProfile:
        """Load query JSON and normalize the query profile using this corpus's stats.

        Args:
            query_path: Path to query object (``profile``, ``weights``, ``k``).

        Returns:
            :class:`VectorizedQueryProfile` with normalized ``vector``, ``weights``, and ``k``.

        Raises:
            ValidationError: If JSON is invalid or vector/weights length mismatch.
        """

        ref_raw: QProfile
        weights: tuple[float, ...]
        k: int
        ref_raw, weights, k = load_query_json(query_path)
        query_vec: tuple[float, ...] = self.normalize_query(ref_raw)
        if len(query_vec) != VECTOR_DIM or len(weights) != VECTOR_DIM:
            raise ValidationError(
                f"query vector length {len(query_vec)} and weights length {len(weights)} "
                f"must equal VECTOR_DIM ({VECTOR_DIM})"
            )
        return VectorizedQueryProfile(
            vector=tuple(query_vec),
            weights=tuple(weights),
            k=k,
        )
