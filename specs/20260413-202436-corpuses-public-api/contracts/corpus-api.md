# Contract: `Corpuses` public corpus API

**Scope**: Runtime Python API for the profile corpus pipeline (not HTTP).  
**Stability**: Intended for use by `services` package code, tests, and course extensions.

## Type

- **`Corpuses`**: `frozen` dataclass with `normalized: tuple[NormalizedProfile, ...]` and `stats: ScalingStats`.

## Factory / lifecycle methods

| Method | Role |
|--------|------|
| `from_raw(raw)` | Two-pass Min–Max build from raw profiles |
| `from_json_path(path)` | Load JSON corpus then `from_raw` |
| `from_normalized(profiles, stats=...)` | Wrap pre-normalized data (e.g. tests) |

## Pipeline building blocks (static / class)

| Method | Role |
|--------|------|
| `degree_to_rank(degree: str) -> float` | Catalog ordinal for degree |
| `domain_to_index(domain: str) -> float` | Catalog index for domain |
| `raw_to_prevector(raw) -> tuple[float, ...]` | Five features before scaling |
| `compute_scaling_stats(pre_vectors) -> ScalingStats` | Min/max over rows |
| `apply_minmax(pre, stats) -> tuple[float, ...]` | Scale one pre-vector |
| `build_normalized_corpus(raw_profiles)` | Returns `(list[NormalizedProfile], ScalingStats)` |
| `normalize_query_raw(raw, stats) -> tuple[float, ...]` | Query vector for given stats |
| `iter_synthetic_profiles(count, *, seed=None)` | Generator of `RawProfile` |

## Instance methods

| Method | Role |
|--------|------|
| `normalize_query(raw)` | Same as `normalize_query_raw(raw, self.stats)` |
| `load_query(query_path)` | JSON query load + normalize reference |

## Removed surfaces

Module-level functions previously defined at the bottom of `dataset.py` (wrappers and `get_synthetic_*` helpers) are **not** part of the contract after this feature; callers must use the table above.
