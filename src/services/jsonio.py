"""JSON load/save for corpus rows and query payloads (stdlib ``json`` only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.constants import QUERY_WEIGHT_KEYS
from services.dto import RawProfile
from services.helper import ValidationError


def load_corpus_json(path: str | Path) -> list[RawProfile]:
    """Load a JSON array of corpus records from disk.

    Args:
        path: File path to UTF-8 JSON array.

    Returns:
        List of :class:`RawProfile` instances.

    Raises:
        ValidationError: If structure or fields are invalid.
    """
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValidationError("corpus JSON must be an array")
    return [_parse_corpus_record(item, i) for i, item in enumerate(raw)]


def _parse_corpus_record(item: Any, index: int) -> RawProfile:
    if not isinstance(item, dict):
        raise ValidationError(f"corpus[{index}] must be an object")
    required = (
        "profile_id",
        "age",
        "monthly_income",
        "daily_learning_hours",
        "highest_degree",
        "favourite_domain",
    )
    for key in required:
        if key not in item:
            raise ValidationError(f"corpus[{index}] missing key {key!r}")
    return RawProfile(
        profile_id=str(item["profile_id"]),
        age=float(item["age"]),
        monthly_income=float(item["monthly_income"]),
        daily_learning_hours=float(item["daily_learning_hours"]),
        highest_degree=str(item["highest_degree"]),
        favourite_domain=str(item["favourite_domain"]),
    )


def load_query_json(
    path: str | Path,
) -> tuple[RawProfile, tuple[float, ...], int]:
    """Load query file: reference profile, weights, and k.

    Args:
        path: UTF-8 JSON object with ``reference``, ``weights``, ``k``.

    Returns:
        ``(reference_raw, weights_tuple, k)`` with weights order matching the
        normalized vector: age, income, education, hours, then one weight per
        domain catalog entry (``QUERY_WEIGHT_KEYS`` order).

    Raises:
        ValidationError: On malformed JSON or invalid values.
    """
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValidationError("query JSON must be an object")
    if "reference" not in doc or "weights" not in doc or "k" not in doc:
        raise ValidationError("query JSON requires reference, weights, k")
    ref = _parse_corpus_record(doc["reference"], -1)
    wobj = doc["weights"]
    if not isinstance(wobj, dict):
        raise ValidationError("weights must be an object")
    weights_list: list[float] = []
    for key in QUERY_WEIGHT_KEYS:
        if key not in wobj:
            raise ValidationError(f"weights missing key {key!r}")
        weights_list.append(float(wobj[key]))
    weights: tuple[float, ...] = tuple(weights_list)
    k = int(doc["k"])
    if k < 1:
        raise ValidationError("k must be at least 1")
    return ref, weights, k


def dump_json(data: object) -> str:
    """Serialize to compact JSON string with ASCII-safe output."""
    return json.dumps(data, indent=2, sort_keys=True)
