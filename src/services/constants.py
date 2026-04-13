"""Shared constants: feature dimension, synthetic catalogs, JSON keys, tolerances."""

from __future__ import annotations

from typing import Final

# Feature dimensionality for profiles, weights, and KD-tree axes.
VECTOR_DIM: Final[int] = 5

DEGREE_CATALOG: Final[tuple[str, ...]] = (
    "none",
    "certificate",
    "associate",
    "bachelor",
    "master",
    "doctorate",
    "postdoc",
)

DOMAIN_CATALOG: Final[tuple[str, ...]] = (
    "software",
    "data_science",
    "finance",
    "healthcare",
    "education",
    "manufacturing",
    "retail",
    "research",
    "design",
    "operations",
)

# Order of keys in query JSON ``weights`` object (matches normalized vector order).
QUERY_WEIGHT_KEYS: Final[tuple[str, ...]] = (
    "age",
    "monthly_income",
    "education",
    "daily_learning_hours",
    "domain",
)

# Absolute tolerance for comparing hit-list distances (baseline vs k-d tree).
HITS_EQUAL_ABS_TOL: Final[float] = 1e-9

# Epsilon when comparing KD lower bound to current worst distance in the heap.
KD_TREE_LB_EPS: Final[float] = 1e-9
