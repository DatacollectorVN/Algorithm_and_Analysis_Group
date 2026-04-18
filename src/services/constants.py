"""Shared constants: feature dimension, synthetic catalogs, JSON keys, tolerances."""

from __future__ import annotations

from typing import Final

# Feature dimensionality for profiles, weights, and KD-tree axes.
# Layout: [age, monthly_income, degree_rank, daily_learning_hours,
#          domain_0, …, domain_9]  (4 numeric + 10 one-hot domain bits)
VECTOR_DIM: Final[int] = 14

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
    "highest_degree",
    "daily_learning_hours",
    "domain_software",
    "domain_data_science",
    "domain_finance",
    "domain_healthcare",
    "domain_education",
    "domain_manufacturing",
    "domain_retail",
    "domain_research",
    "domain_design",
    "domain_operations",
)

# Absolute tolerance for comparing hit-list distances (baseline vs k-d tree).
HITS_EQUAL_ABS_TOL: Final[float] = 1e-9

# Epsilon when comparing KD lower bound to current worst distance in the heap.
KD_TREE_LB_EPS: Final[float] = 1e-9
