"""Immutable domain records for profiles (data transfer only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.constants import DEGREE_CATALOG, DOMAIN_CATALOG

type ProfileVector = tuple[float, ...]


@dataclass(frozen=True, slots=True)
class Profile:
    """One raw user record before normalization."""

    profile_id: int
    age: float
    monthly_income: float
    self_learning_hours: float
    highest_degree: str
    favourite_domain: str

    @classmethod
    def init_from_json(cls, item: Any, *, label: str) -> Profile:
        """Build from one profile-shaped JSON ``dict`` (corpus row or query ``profile``).

        Raises:
            Exception: If ``item`` is not a ``dict``.
            KeyError, TypeError, ValueError: If a required field is missing or not coercible.
        """
        if not isinstance(item, dict):
            raise Exception(f"{label} must be an object")
        return cls(
            profile_id=int(item["profile_id"]),
            age=float(item["age"]),
            monthly_income=float(item["monthly_income"]),
            self_learning_hours=float(item["self_learning_hours"]),
            highest_degree=str(item["highest_degree"]),
            favourite_domain=str(item["favourite_domain"]),
        )

@dataclass(frozen=True, slots=True)
class QProfile:
    """The Query field in the query JSON."""
    age: float
    monthly_income: float
    self_learning_hours: float
    highest_degree: str
    favourite_domain: str

    @classmethod
    def init_from_json(cls, item: Any, *, label: str) -> QProfile:
        """Build from one profile-shaped JSON ``dict`` (corpus row or query ``profile``).

        Raises:
            Exception: If ``item`` is not a ``dict``.
            KeyError, TypeError, ValueError: If a required field is missing or not coercible.
        """
        if not isinstance(item, dict):
            raise Exception(f"{label} must be an object")
        return cls(
            age=float(item["age"]),
            monthly_income=float(item["monthly_income"]),
            self_learning_hours=float(item["self_learning_hours"]),
            highest_degree=str(item["highest_degree"]),
            favourite_domain=str(item["favourite_domain"]),
        )

@dataclass(frozen=True, slots=True)
class QueryProfile:
    """Query file payload: ``profile``, ``weights`` (JSON object), and ``k``.

    Matches the top-level shape of query JSON (see ``samples/test.json``).
    """

    profile: QProfile
    weights: tuple[tuple[str, Any], ...]
    k: int

    def weights_dict(self) -> dict[str, Any]:
        """Mutable view of weight entries for downstream resolution to a 9-tuple."""
        return dict(self.weights)

    @staticmethod
    def from_document(doc: Any) -> QueryProfile:
        """Validate and build from the decoded JSON root object."""
        from services.helper import ValidationError

        if not isinstance(doc, dict):
            raise ValidationError("query JSON must be an object")
        if "profile" not in doc or "weights" not in doc or "k" not in doc:
            raise ValidationError("query JSON requires profile, weights, k")
        wobj = doc["weights"]
        if not isinstance(wobj, dict):
            raise ValidationError("weights must be an object")
        k = int(doc["k"])
        if k < 1 or k > 20:
            raise ValidationError("k must be between 1 and 20")
        profile = QProfile.init_from_json(doc["profile"], label="profile")
        if profile.highest_degree not in DEGREE_CATALOG:
            raise ValidationError(f"profile.highest_degree not in catalog: {profile.highest_degree!r}")
        if profile.favourite_domain not in DOMAIN_CATALOG:
            raise ValidationError(f"profile.favourite_domain not in catalog: {profile.favourite_domain!r}")
        weights_pairs = tuple(sorted(wobj.items(), key=lambda t: t[0]))
        return QueryProfile(profile=profile, weights=weights_pairs, k=k)


@dataclass(frozen=True, slots=True)
class VectorizedProfile:
    """Corpus point in [0, 1]^9 after Min–Max scaling and one-hot encoding.

    The vector layout is:
    [age, monthly_income, degree_rank, self_learning_hours,
     domain_0, domain_1, …, domain_4]
    where degree_rank is an ordinal encoding and the five domain dimensions
    are one-hot bits (exactly one 1.0, the rest 0.0).
    """

    profile_id: int
    vector: ProfileVector


@dataclass(frozen=True, slots=True)
class VectorizedQueryProfile:
    """Normalized query: reference vector, per-dimension weights, and ``k``."""
    vector: ProfileVector
    weights: ProfileVector
    k: int


@dataclass(frozen=True, slots=True)
class ScalingStats:
    """Per-dimension Min–Max parameters from a corpus (9 dimensions).

    Indices 0–3 hold computed min/max for numeric features.
    Indices 4–8 hold placeholder values (min=0.0, max=1.0) for
    one-hot domain bits, which are not Min–Max scaled.
    """

    mins: ProfileVector
    maxs: ProfileVector


@dataclass(frozen=True, slots=True)
class TopKResult:
    """Top-k result: profile_id and distance."""

    profile_ids: tuple[int, ...]
    distances: tuple[float, ...]

    def __len__(self) -> int:
        return len(self.profile_ids)

    def __getitem__(self, index: int) -> tuple[int, float]:
        return (self.profile_ids[index], self.distances[index])

    def __iter__(self):  # type: ignore[override]
        return zip(self.profile_ids, self.distances)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TopKResult):
            return self.profile_ids == other.profile_ids and self.distances == other.distances
        if isinstance(other, list):
            return list(self) == other
        return NotImplemented