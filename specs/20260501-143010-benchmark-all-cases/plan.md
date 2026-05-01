# Implementation Plan: Benchmark All Cases — KD-tree vs Baseline

**Branch**: `20260501-143010-benchmark-all-cases` | **Date**: 2026-05-01 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `specs/20260501-143010-benchmark-all-cases/spec.md`  
**Note**: Working on branch `feature/enhancement` (no new branch per user preference).

## Summary

Add a new interactive menu option ("Run All Cases Benchmark: Baseline vs KD-tree") that accepts user-specified dataset sizes and k values, generates or reuses datasets of each size, builds both strategies once per size, and produces a four-section report: effect of dataset size, effect of k value, effect of attribute weights, and a correctness verification summary confirming KD-tree produces identical results to Baseline across all tested cases.

## Technical Context

**Language/Version**: Python 3.12 (`type` alias syntax, `from __future__ import annotations`)  
**Primary Dependencies**: Standard Library only — `random`, `time`, `json`, `pathlib`, `dataclasses` (no PyPI packages)  
**Storage**: Filesystem — `.rmit/dataset/<stamp>/profiles.json` (generated per dataset size); no pickle cache for this option  
**Testing**: `unittest` (Standard Library only)  
**Target Platform**: CLI, any Python 3.12+ install  
**Project Type**: CLI tool  
**Performance Goals**: Build + search time must complete within 120 s for dataset sizes up to 1,000,000 profiles on developer hardware  
**Constraints**: No third-party packages; weights vector is always 9-dimensional matching `VECTOR_DIM`; k is validated against dataset size  
**Scale/Scope**: Up to ~3 dataset sizes and ~5 k values per run (combinatorial cases stay manageable)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Standard Library First | **PASS** — no new imports beyond what menu.py already uses (`random`, `time`, `pathlib`, `json`) | |
| PEP 8 + Type Hints | **PASS** — new functions use modern type hints (`list[int]`, `tuple[float, ...]`) | |
| Google-style Docstrings | **PASS** — required on all new public/non-trivial functions | |
| Domain Errors via Exception Hierarchies | **PASS** — reuse existing `ValidationError`; no bare except | |
| Algorithmic Efficiency | **PASS** — benchmark loop is O(S × K × W) where S, K, W are small user-provided constants; no asymptotic degradation | |
| No complexity deviation requiring justification | **PASS** | |

## Project Structure

### Documentation (this feature)

```text
specs/20260501-143010-benchmark-all-cases/
├── plan.md              # This file
├── research.md          # Phase 0 — codebase analysis & design decisions
├── data-model.md        # Phase 1 — new data structures
├── quickstart.md        # Phase 1 — how to test/run the new option
└── checklists/
    └── requirements.md  # Spec quality checklist (already created)
```

### Source Code Changes

```text
src/
└── services/
    └── menu.py          # All changes are confined to this single file
        # NEW: _WEIGHT_SCENARIOS constant
        # NEW: _input_int_list() helper
        # NEW: _find_or_generate_dataset_for_size() helper
        # NEW: _vectorized_query_direct() helper (bypasses file I/O)
        # NEW: _do_benchmark_all_cases() menu action
        # NEW: _print_all_cases_report() report renderer (4 sections)
        # MODIFIED: _MENU string — add option 5, renumber Exit to 6
        # MODIFIED: interactive_menu() — add "5" → _do_benchmark_all_cases, exit → "6"

tests/
└── test_benchmark_all_cases.py   # New unittest covering new helpers and report sections
```

**Structure Decision**: Single-file change to `menu.py`; all new logic is self-contained in that module, consistent with how `_do_benchmark` is already structured. No new modules are needed.

## Complexity Tracking

> No constitution violations to justify.
