"""Shared constants: feature dimension, synthetic catalogs, JSON keys, tolerances."""

from __future__ import annotations

from typing import Final

# Feature dimensionality for profiles, weights, and KD-tree axes.
# Layout: [age, monthly_income, degree_rank, self_learning_hours,
#          domain_0, …, domain_4]  (4 numeric + 5 one-hot domain bits)
VECTOR_DIM: Final[int] = 9

DEGREE_CATALOG: Final[tuple[str, ...]] = (
    "high_school",
    "bachelor",
    "master",
    "phd",
)

DOMAIN_CATALOG: Final[tuple[str, ...]] = (
    "ai",
    "software_engineering",
    "data_science",
    "cybersecurity",
    "business_analytics",
)

# Order of keys in query JSON ``weights`` object (matches normalized vector order).
QUERY_WEIGHT_KEYS: Final[tuple[str, ...]] = (
    "age",
    "monthly_income",
    "highest_degree",
    "self_learning_hours",
    "domain_ai",
    "domain_software_engineering",
    "domain_data_science",
    "domain_cybersecurity",
    "domain_business_analytics",
)

# Absolute tolerance for comparing hit-list distances (baseline vs k-d tree).
HITS_EQUAL_ABS_TOL: Final[float] = 1e-9

# Epsilon when comparing KD lower bound to current worst distance in the heap.
KD_TREE_LB_EPS: Final[float] = 1e-9
