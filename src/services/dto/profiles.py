"""Immutable domain records for profiles (data transfer only)."""

from __future__ import annotations

from dataclasses import dataclass

type ProfileVector = tuple[float, ...]


@dataclass(frozen=True, slots=True)
class RawProfile:
    """One raw user record before normalization."""

    profile_id: str
    age: float
    monthly_income: float
    daily_learning_hours: float
    highest_degree: str
    favourite_domain: str


@dataclass(frozen=True, slots=True)
class NormalizedProfile:
    """Corpus point in [0, 1]^14 after Min–Max scaling and one-hot encoding.

    The vector layout is:
    [age, monthly_income, degree_rank, daily_learning_hours,
     domain_0, domain_1, …, domain_9]
    where degree_rank is an ordinal encoding and the ten domain dimensions
    are one-hot bits (exactly one 1.0, the rest 0.0).
    """

    profile_id: str
    vector: ProfileVector


@dataclass(frozen=True, slots=True)
class ScalingStats:
    """Per-dimension Min–Max parameters from a corpus (14 dimensions).

    Indices 0–3 hold computed min/max for numeric features.
    Indices 4–13 hold placeholder values (min=0.0, max=1.0) for
    one-hot domain bits, which are not Min–Max scaled.
    """

    mins: ProfileVector
    maxs: ProfileVector
