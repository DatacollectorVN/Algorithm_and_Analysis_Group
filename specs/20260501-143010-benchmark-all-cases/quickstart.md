# Quickstart: Benchmark All Cases

**Phase 1 output** | Feature: `20260501-143010-benchmark-all-cases`

---

## How to Run

```bash
cd src
python main.py
```

Select option **5** from the menu:

```
  5. Run All Cases Benchmark: Baseline vs KD-tree
```

Follow the prompts:

```
Enter dataset sizes (comma-separated, e.g. 10000,100000): 10000,50000
Enter k values (comma-separated, e.g. 2,5,10): 2,5,10
```

The benchmark will:
1. Find or generate datasets for each requested size (seed=42, reproducible).
2. Build both Baseline and KD-tree strategies for each size.
3. Run all cases and display a four-section report.

---

## Expected Output (abbreviated)

```
========================================
  BENCHMARK — ALL CASES
========================================

--- Section 1: Effect of Dataset Size ---
  (k=2, weights=Uniform, random query per size)
  Size       Baseline Build   KD-tree Build   Baseline Search   KD-tree Search   Speedup
  10,000           42.1 ms         95.3 ms            3.2 ms          0.08 ms    40.0×
  50,000          210.4 ms        487.2 ms           16.1 ms          0.12 ms   134.2×

--- Section 2: Effect of k Value ---
  (size=10000, weights=Uniform, random query per k)
  k    Baseline Search   KD-tree Search   Speedup
  2           3.2 ms          0.08 ms    40.0×
  5           3.3 ms          0.11 ms    30.0×
  10          3.5 ms          0.15 ms    23.3×

--- Section 3: Effect of Attribute Weights ---
  (size=10000, k=2, fixed query profile: "Young AI enthusiast (age 22, bachelor)")
  Weight Scenario          Baseline Search   KD-tree Search   Speedup
  Uniform (all 1.0)               3.2 ms          0.08 ms    40.0×
  Domain-heavy (domain ×5)        3.1 ms          0.09 ms    34.4×
  Degree-heavy (degree ×5)        3.2 ms          0.07 ms    45.7×
  Income-heavy (income ×5)        3.3 ms          0.08 ms    41.3×

--- Section 4: Correctness Verification ---
  Size    k   Weight Scenario          Profile                        Match?
  10,000  2   Uniform (all 1.0)        Young AI enthusiast             ✓
  10,000  2   Domain-heavy (domain ×5) Young AI enthusiast             ✓
  ...
  Correctness: 12/12 cases passed (100%)
========================================
```

---

## How to Run Tests

```bash
cd src
python -m pytest ../tests/test_benchmark_all_cases.py -v
```

Tests cover:
- `_input_int_list` parsing (valid, invalid, empty, duplicates)
- `_find_or_generate_dataset_for_size` with mocked filesystem
- `_run_case` correctness flag logic
- `_print_all_cases_report` output format (captured stdout)
