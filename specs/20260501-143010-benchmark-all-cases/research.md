# Research: Benchmark All Cases — KD-tree vs Baseline

**Phase 0 output** | Feature: `20260501-143010-benchmark-all-cases`

---

## 1. How the Existing Benchmark Works

**Decision**: Reuse `build_searcher` / `get_topk` from `services/search/strategies/base.py` directly.  
**Rationale**: These are already the timing primitives used by `_do_benchmark`. Reusing them keeps timing methodology consistent.  
**Alternatives considered**: `timed_searcher_construct` / `timed_search` from `benchmark.py` — functionally equivalent but `build_searcher`/`get_topk` are what the menu already uses; no reason to switch.

---

## 2. Vectorizing a Query Without File I/O

**Decision**: Build `VectorizedQueryProfile` directly by calling `corpuses.normalize_query(qprofile)` and supplying a pre-built weights tuple, rather than writing a temp file and calling `corpuses.build_vectorized_query(path)`.

**Rationale**: The all-cases runner fires many (size × k × weight) queries; creating a temp file per query is unnecessary I/O. The `VectorizedQueryProfile` constructor is public and its 3 fields (`vector`, `weights`, `k`) can be populated without file access:
```python
vector = corpuses.normalize_query(qprofile)   # uses corpus scaling stats
weights = weight_tuple                          # pre-built 9-tuple
vq = VectorizedQueryProfile(vector=vector, weights=weights, k=k)
```
`Corpuses.normalize_query` applies the same Min–Max transform that `build_vectorized_query` applies; the result is identical.

**Alternatives considered**: Temp file per query (matches existing `_do_benchmark` exactly) — rejected because it adds disk I/O proportional to the number of cases; too slow for large runs.

---

## 3. Dataset Generation Per Size

**Decision**: Scan `.rmit/dataset/*/metadata.txt` for `N=<requested_size>`; reuse the first match, otherwise call `run_generate_corpus(size, seed=42)` and re-scan.

**Rationale**: Avoids generating a dataset that already exists on disk. The seed is fixed at 42 for reproducibility.

**Alternatives considered**: Always regenerate — deterministic but wasteful for repeated runs with the same sizes.

---

## 4. Weight Scenarios (Effect of Attribute Weights)

**Decision**: Define a module-level `_WEIGHT_SCENARIOS` list of `{"label": str, "weights": tuple[float, ...]}` dicts, where each weight tuple is 9-dimensional in `QUERY_WEIGHT_KEYS` order:  
`(age, monthly_income, self_learning_hours, highest_degree, domain_ai, domain_software_engineering, domain_data_science, domain_cybersecurity, domain_business_analytics)`

Four scenarios:
| Label | Description |
|-------|-------------|
| Uniform (all 1.0) | Baseline equal-weight configuration |
| Domain-heavy (domain ×5) | All 5 domain dimensions = 5.0, others = 1.0 |
| Degree-heavy (degree ×5) | `highest_degree` = 5.0, others = 1.0 |
| Income-heavy (income ×5) | `monthly_income` = 5.0, others = 1.0 |

**Rationale**: Covers uniform, categorical (domain), ordinal (degree), and continuous (income) weight emphasis cases. Four scenarios is enough to show variance without creating an overwhelming report.

**Alternatives considered**: Using the JSON "domain" shorthand — rejected because it requires a profile's `favourite_domain` field and couples weight construction to the profile choice, making it less general.

---

## 5. Random Profile Selection

**Decision**: Use `random.Random(seed=None)` (fresh RNG per run, not seeded) to pick one profile from `_SAMPLE_PROFILES` per case, so different cases use different query profiles even within a single run.

**Rationale**: Prevents the benchmark from being artificially biased by always using the same query; adds breadth to correctness verification.  
**Alternatives considered**: Round-robin assignment (predictable but less interesting for a benchmark) — retained as fallback if we need determinism.

---

## 6. Correctness Verification

**Decision**: After each (dataset, k, weights, profile) case, compare `TopKResult.profile_ids` (exact match) and `TopKResult.distances` (within `HITS_EQUAL_ABS_TOL = 1e-9`). Track per-case pass/fail and print a summary table.

**Rationale**: `TopKResult.__eq__` already exists but compares distances exactly. For floating-point robustness we compare distances with the tolerance constant `HITS_EQUAL_ABS_TOL` from `services/constants.py`, matching the approach in `tests/test_equivalence.py`.

**Alternatives considered**: Exact equality (`==`) — too strict for float arithmetic across strategies; tolerance match is the established project pattern.

---

## 7. Report Sections

The four requested sections map to:

| Section | Fixed | Varied | Profile Selection |
|---------|-------|--------|------------------|
| Effect of dataset size | k = k_values[0], weights = uniform | dataset_size | random per size |
| Effect of k value | size = dataset_sizes[0], weights = uniform | k | random per k |
| Effect of attribute weights | size = dataset_sizes[0], k = k_values[0] | weight scenario | fixed (first sample profile) |
| Correctness verification | — | all (size, k, weight) combinations | random per combination |

Build time is shown once per dataset size (not repeated per k or weight), since the strategy is built once and shared.

---

## 8. No New Modules

All new logic lives in `menu.py`. No new source files are required. A new test file `tests/test_benchmark_all_cases.py` tests the new helper functions in isolation.
