# Data Model: Benchmark All Cases

**Phase 1 output** | Feature: `20260501-143010-benchmark-all-cases`

---

## New Constants

### `_WEIGHT_SCENARIOS` (added to `menu.py`)

```
List of weight configuration dicts. Each dict:
  label:   str                        — human-readable name for report
  weights: tuple[float, ...] (len=9) — 9-dimensional weight tuple in QUERY_WEIGHT_KEYS order
```

Layout of the weights tuple (9 dimensions):
```
Index  Field
0      age
1      monthly_income
2      self_learning_hours
3      highest_degree
4      domain_ai
5      domain_software_engineering
6      domain_data_science
7      domain_cybersecurity
8      domain_business_analytics
```

Four scenarios defined:
```
("Uniform (all 1.0)",          (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0))
("Domain-heavy (domain ×5)",   (1.0, 1.0, 1.0, 1.0, 5.0, 5.0, 5.0, 5.0, 5.0))
("Degree-heavy (degree ×5)",   (1.0, 1.0, 1.0, 5.0, 1.0, 1.0, 1.0, 1.0, 1.0))
("Income-heavy (income ×5)",   (1.0, 5.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0))
```

---

## New Internal Data Structures (dicts, not dataclasses)

### `BuiltStrategies` (dict, per dataset size)
```
{
  "corpuses":  Corpuses          — loaded corpus for this size
  "baseline":  BaselineSearcher  — built baseline strategy instance
  "kdtree":    KDTreeSearcher    — built KD-tree strategy instance
  "b_build":   float             — baseline build time in seconds
  "k_build":   float             — KD-tree build time in seconds
  "path":      Path              — path to the dataset JSON
}
```

### `CaseRecord` (dict, one per benchmark case)
```
{
  "dataset_size":    int          — corpus size
  "k":               int          — top-k count
  "weight_label":    str          — weight scenario name
  "profile_label":   str          — sample profile label (or "random")
  "b_search":        float        — baseline search time (seconds)
  "k_search":        float        — KD-tree search time (seconds)
  "speedup":         float        — b_search / k_search (> 1 means KD-tree faster)
  "correct":         bool         — True if KD-tree matches baseline within HITS_EQUAL_ABS_TOL
}
```

---

## New Helper Functions (all in `menu.py`)

### `_input_int_list(prompt: str) -> list[int]`
```
Reads a comma-separated string of positive integers from stdin.
Reprompts until all values are valid positive integers.
Returns a deduplicated, sorted list.
```

### `_find_or_generate_dataset_for_size(size: int) -> Path | None`
```
Scans .rmit/dataset/*/metadata.txt for N=<size>.
Returns the matching profiles.json path if found.
Otherwise calls run_generate_corpus(size, seed=42) and rescans.
Returns None only if generation fails.
```

### `_build_strategies_for_corpuses(corpuses: Corpuses) -> tuple[object, float, object, float]`
```
Calls build_searcher(BaselineSearcher, corpuses) and build_searcher(KDTreeSearcher, corpuses).
Returns (baseline_searcher, b_build_seconds, kdtree_searcher, k_build_seconds).
```

### `_run_case(baseline, kdtree, corpuses, profile_dict, weights, k) -> CaseRecord partial`
```
Builds VectorizedQueryProfile directly (no temp file).
Calls get_topk for both strategies.
Compares results for correctness (profile_ids exact, distances within HITS_EQUAL_ABS_TOL).
Returns timing and correctness fields (caller fills dataset_size, k, weight_label, profile_label).
```

### `_do_benchmark_all_cases() -> None`
```
Top-level menu action. Orchestrates:
  1. Prompt for dataset sizes and k values (via _input_int_list).
  2. For each size: find/generate dataset, build both strategies.
  3. Section 1: effect of dataset size (fixed k=k_values[0], uniform weights, random profile per size).
  4. Section 2: effect of k value (fixed size=dataset_sizes[0], uniform weights, random profile per k).
  5. Section 3: effect of weights (fixed size=dataset_sizes[0], k=k_values[0], 4 weight scenarios, fixed profile).
  6. Collect all cases for correctness check.
  7. Print full report via _print_all_cases_report().
```

### `_print_all_cases_report(size_rows, k_rows, weight_rows, all_rows) -> None`
```
Renders the four-section console report:
  - Section 1: Effect of Dataset Size (table: size | b_build | k_build | b_search | k_search | speedup)
  - Section 2: Effect of k Value (table: k | b_search | k_search | speedup)
  - Section 3: Effect of Attribute Weights (table: weight scenario | b_search | k_search | speedup)
  - Section 4: Correctness Verification (table: size | k | weight | profile | match?)
```

---

## Modified Structures

### `_MENU` string
```
Before (5 options):
  1. Generate dataset
  2. Search with Baseline strategy
  3. Search with KD-tree strategy
  4. Simple Benchmark: Baseline vs KD-tree
  5. Exit

After (6 options):
  1. Generate dataset
  2. Search with Baseline strategy
  3. Search with KD-tree strategy
  4. Simple Benchmark: Baseline vs KD-tree
  5. Run All Cases Benchmark: Baseline vs KD-tree
  6. Exit
```

### `interactive_menu()` `_ACTIONS` dict
```
Add: "5" → ("Run All Cases Benchmark", _do_benchmark_all_cases)
Change exit check: "5" → "6"
Change prompt: "Enter option [1-5]:" → "Enter option [1-6]:"
Change invalid message: "1–5" → "1–6"
```
