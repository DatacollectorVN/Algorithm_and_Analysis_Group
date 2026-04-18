"""JSON load/save for corpus rows and query payloads (stdlib ``json`` only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.constants import DOMAIN_CATALOG, QUERY_WEIGHT_KEYS
from services.dto import Profile, QProfile, QueryProfile
from services.helper import ValidationError


def load_corpus_json(path: str | Path) -> list[Profile]:
    """Load a JSON array of corpus records from disk.

    Args:
        path: File path to UTF-8 JSON array.

    Returns:
        List of :class:`Profile` instances.

    Raises:
        ValidationError: If structure or fields are invalid.
    """
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValidationError("corpus JSON must be an array")
    return [Profile.init_from_json(item, label=f"corpus[{i}]") for i, item in enumerate(raw)]


def _float_weight(value: Any, *, key: str) -> float:
    if isinstance(value, bool):
        raise ValidationError(f"weights.{key} must be a number, not bool")
    if isinstance(value, (int, float)):
        return float(value)
    raise ValidationError(f"weights.{key} must be a number")


def _degree_weight(wobj: dict[str, Any]) -> float:
    if "highest_degree" not in wobj:
        raise ValidationError("weights missing key 'highest_degree'")
    return _float_weight(wobj["highest_degree"], key="highest_degree")


def _domain_weight_keys() -> tuple[str, ...]:
    return QUERY_WEIGHT_KEYS[4:]


def _shorthand_domain_scalar(wobj: dict[str, Any]) -> float | None:
    """Scalar weight applied along the profile domain one-hot axis, or None if absent."""
    if "domain" in wobj:
        return _float_weight(wobj["domain"], key="domain")
    if "favourite_domain" in wobj:
        v = wobj["favourite_domain"]
        if isinstance(v, str):
            raise ValidationError(
                "weights.favourite_domain must be a number when used as a domain weight; "
                "put the domain string on profile.favourite_domain"
            )
        return _float_weight(v, key="favourite_domain")
    return None


def _weights_tuple(wobj: dict[str, Any], profile: Profile | QProfile) -> tuple[float, ...]:
    age = _float_weight(wobj["age"], key="age")
    income = _float_weight(wobj["monthly_income"], key="monthly_income")
    deg_w = _degree_weight(wobj)
    hours = _float_weight(wobj["daily_learning_hours"], key="daily_learning_hours")

    domain_keys = _domain_weight_keys()
    explicit = [k for k in domain_keys if k in wobj]
    shorthand = _shorthand_domain_scalar(wobj)

    if explicit and shorthand is not None:
        raise ValidationError(
            "weights: use either all domain_* keys or a single domain shorthand "
            "('domain' or numeric 'favourite_domain'), not both"
        )
    if explicit:
        if len(explicit) != len(domain_keys):
            raise ValidationError(
                f"weights: expected all {len(domain_keys)} domain_* keys, "
                f"missing {[k for k in domain_keys if k not in wobj]!r}"
            )
        domain_weights = [_float_weight(wobj[k], key=k) for k in domain_keys]
    elif shorthand is not None:
        try:
            idx = DOMAIN_CATALOG.index(profile.favourite_domain)
        except ValueError as exc:
            raise ValidationError(
                f"profile.favourite_domain {profile.favourite_domain!r} is not in catalog"
            ) from exc
        domain_weights = [0.0] * len(domain_keys)
        domain_weights[idx] = shorthand
    else:
        raise ValidationError(
            "weights: provide all per-domain keys "
            f"({domain_keys[0]!r} …) or a single 'domain' / numeric 'favourite_domain' weight"
        )

    return (age, income, deg_w, hours, *domain_weights)


def load_query_json(
    path: str | Path,
) -> tuple[QProfile, tuple[float, ...], int]:
    """Load query file: profile, weights, and k.

    The file is parsed into :class:`~services.dto.QueryProfile`, then weights are
    resolved to a 14-float tuple in ``QUERY_WEIGHT_KEYS`` order.

    Args:
        path: UTF-8 JSON object with ``profile``, ``weights``, ``k``.

    Returns:
        ``(qprofile, weights_tuple, k)`` with weights in ``QUERY_WEIGHT_KEYS`` order.
        Query ``profile`` objects do not require ``profile_id`` (see :class:`~services.dto.QProfile`).

    Raises:
        ValidationError: On malformed JSON or invalid values.
    """
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    qp = QueryProfile.from_document(doc)
    weights = _weights_tuple(qp.weights_dict(), qp.profile)
    if len(weights) != len(QUERY_WEIGHT_KEYS):
        raise ValidationError("internal error: weights length mismatch")

    return qp.profile, weights, qp.k


def dump_json(data: object) -> str:
    """Serialize to compact JSON string with ASCII-safe output."""
    return json.dumps(data, indent=2, sort_keys=True)
