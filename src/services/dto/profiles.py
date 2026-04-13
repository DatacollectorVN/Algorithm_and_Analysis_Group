"""Immutable domain records for profiles (data transfer only)."""

from __future__ import annotations

from dataclasses import dataclass

type ProfileVector = tuple[float, float, float, float, float]


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
    """Corpus point in [0, 1]^5 after Min–Max scaling."""

    profile_id: str
    vector: ProfileVector


@dataclass(frozen=True, slots=True)
class ScalingStats:
    """Per-dimension Min–Max parameters from a corpus."""

    mins: ProfileVector
    maxs: ProfileVector
