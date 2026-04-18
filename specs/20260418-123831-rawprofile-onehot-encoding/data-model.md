# Data Model: One-Hot Encoding for favourite_domain

**Branch**: `20260418-123831-rawprofile-onehot-encoding`  
**Phase**: 1 — Design  
**Date**: 2026-04-18

---

## Vector Layout (after this change)

| Index | Field | Encoding | Scaling |
|-------|-------|----------|---------|
| 0 | age | raw float | Min–Max |
| 1 | monthly_income | raw float | Min–Max |
| 2 | highest_degree | ordinal rank (0–6) | Min–Max |
| 3 | daily_learning_hours | raw float | Min–Max |
| 4 | domain: software | one-hot bit (0.0 or 1.0) | none |
| 5 | domain: data_science | one-hot bit | none |
| 6 | domain: finance | one-hot bit | none |
| 7 | domain: healthcare | one-hot bit | none |
| 8 | domain: education | one-hot bit | none |
| 9 | domain: manufacturing | one-hot bit | none |
| 10 | domain: retail | one-hot bit | none |
| 11 | domain: research | one-hot bit | none |
| 12 | domain: design | one-hot bit | none |
| 13 | domain: operations | one-hot bit | none |

**Total dimensions**: 14 (was 5)

---

## Entity Changes

### `ProfileVector` (`src/services/dto/profiles.py`)

```
Before: type ProfileVector = tuple[float, float, float, float, float]
After:  type ProfileVector = tuple[float, ...]
```

- Variable-length homogeneous tuple; `VECTOR_DIM` (now 14) is the authoritative length constraint enforced at runtime by `distance.py` and `weighted_sq_dist_query_to_box`.

---

### `ScalingStats` (`src/services/dto/profiles.py`)

```
Before: mins: tuple[float, float, float, float, float]
        maxs: tuple[float, float, float, float, float]

After:  mins: tuple[float, ...]   (14 values)
        maxs: tuple[float, ...]   (14 values)
```

- Indices 0–3: computed Min–Max bounds from corpus.
- Indices 4–13: placeholder (min=0.0, max=1.0); never consumed for scaling.

---

### `NormalizedProfile` (`src/services/dto/profiles.py`)

- `vector: ProfileVector` — type alias updated (see above); docstring updated to reflect `[0, 1]^14`.

---

### `VECTOR_DIM` (`src/services/constants.py`)

```
Before: VECTOR_DIM: Final[int] = 5
After:  VECTOR_DIM: Final[int] = 14
```

---

### `QUERY_WEIGHT_KEYS` (`src/services/constants.py`)

```
Before: ("age", "monthly_income", "education", "daily_learning_hours", "domain")

After:  (
    "age", "monthly_income", "education", "daily_learning_hours",
    "domain_software", "domain_data_science", "domain_finance",
    "domain_healthcare", "domain_education", "domain_manufacturing",
    "domain_retail", "domain_research", "domain_design", "domain_operations",
)
```

---

## Function Contract Changes

### `Corpuses.domain_to_onehot(domain: str) -> tuple[float, ...]` (NEW — `src/services/dataset.py`)

Replaces `domain_to_index`. Returns a 10-float one-hot tuple.

```
Args:
    domain: Value from DOMAIN_CATALOG.
Returns:
    Tuple of 10 floats: 1.0 at the catalog index of domain, 0.0 elsewhere.
Raises:
    ValidationError: If domain is not in DOMAIN_CATALOG.
```

### `Corpuses.domain_to_index` (REMOVED)

No longer part of the public API. Callers updated to `domain_to_onehot`.

---

### `Corpuses.raw_to_prevector(raw: RawProfile) -> tuple[float, ...]` (`src/services/dataset.py`)

```
Before: returns (age, income, degree_rank, hours, domain_index)  — 5 floats
After:  returns (age, income, degree_rank, hours, *domain_onehot) — 14 floats
```

Layout: `[age, monthly_income, degree_rank, daily_learning_hours, d0, d1, …, d9]`

---

### `Corpuses.apply_minmax(pre, stats) -> tuple[float, ...]` (`src/services/dataset.py`)

```
Before: scales all 5 dimensions using stats.
After:  scales indices 0–3 using stats; copies indices 4–13 as-is (one-hot passthrough).
```

---

### `Corpuses.compute_scaling_stats(pre_vectors) -> ScalingStats` (`src/services/dataset.py`)

- Computes min/max across all 14 dimensions.
- Domain slots (indices 4–13) will have min=0.0 and max=1.0 (or 0.0 if a domain is absent from corpus — the `hi==lo` guard in `minmax_scalar` handles this safely since `apply_minmax` bypasses domain slots anyway).

---

### `load_query_json` (`src/services/jsonio.py`)

```
Before: weights built as explicit 5-tuple: (w[0], w[1], w[2], w[3], w[4])
After:  weights built as tuple(weights_list) — 14-tuple driven by QUERY_WEIGHT_KEYS iteration
```

---

### `union_bbox` / `bbox_of_point` (`src/services/helper.py`)

```
Before: Hard-coded 5-element tuple construction with explicit index [0]…[4]
After:  Loop-based construction driven by VECTOR_DIM
```

Example refactor for `union_bbox`:
```python
lo: ProfileVector = tuple(min(lo1[i], lo2[i]) for i in range(VECTOR_DIM))  # type: ignore[assignment]
hi: ProfileVector = tuple(max(hi1[i], hi2[i]) for i in range(VECTOR_DIM))  # type: ignore[assignment]
```

---

## Query JSON Format Change

Old query JSON (5 weights):
```json
{
  "reference": { ... },
  "weights": {
    "age": 1.0,
    "monthly_income": 1.0,
    "education": 1.0,
    "daily_learning_hours": 1.0,
    "domain": 1.0
  },
  "k": 5
}
```

New query JSON (14 weights):
```json
{
  "reference": { ... },
  "weights": {
    "age": 1.0,
    "monthly_income": 1.0,
    "education": 1.0,
    "daily_learning_hours": 1.0,
    "domain_software": 1.0,
    "domain_data_science": 1.0,
    "domain_finance": 1.0,
    "domain_healthcare": 1.0,
    "domain_education": 1.0,
    "domain_manufacturing": 1.0,
    "domain_retail": 1.0,
    "domain_research": 1.0,
    "domain_design": 1.0,
    "domain_operations": 1.0
  },
  "k": 5
}
```

---

## Validation Rules (unchanged)

- `favourite_domain` must be a member of `DOMAIN_CATALOG`; raises `ValidationError` otherwise.
- `highest_degree` must be a member of `DEGREE_CATALOG`; raises `ValidationError` otherwise.
- Corpus must be non-empty; raises `ValidationError` otherwise.
- All weight values must be finite, non-negative, with at least one positive.

---

## State Transitions

No state machine changes. The normalization pipeline remains a stateless, pure-function two-pass process:

1. **Encode pass**: `raw_to_prevector` on each raw profile → list of 14-float pre-vectors.
2. **Stats pass**: `compute_scaling_stats` → `ScalingStats` (14-dim).
3. **Scale pass**: `apply_minmax` on each pre-vector → `NormalizedProfile` with 14-dim vector.
