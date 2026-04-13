# Implementation Plan: Corpus pipeline public API

**Branch**: `20260413-202436-corpuses-public-api` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/20260413-202436-corpuses-public-api/spec.md`, plus planning note: expose `Corpuses` helpers as public API and **remove** module-level aliases in `src/services/dataset.py` (former lines ~196–256).

**Note**: Planning input **supersedes** spec assumption that “module-level convenience functions may continue to exist”; removal of those aliases is in scope for this implementation.

## Summary

Promote all underscore-prefixed static/class helpers on `Corpuses` to documented public methods (same behavior and signatures as today’s `_`-prefixed implementations). Delete the thin module-level wrapper functions that only delegated to those private methods, plus the unused `load_corpus_from_path` / `get_synthetic_corpus` / `get_synthetic_query` helpers if nothing in-repo imports them. Update imports and `services.__all__` so callers use `Corpuses` (and existing `from_raw` / `from_json_path` / instance `normalize_query` / `load_query`) directly. Refresh class and method docstrings so nothing describes promoted helpers as internal-only.

## Technical Context

**Language/Version**: Python ≥3.12 (`requires-python` in `pyproject.toml`)  
**Primary Dependencies**: Standard library only at runtime (project constitution)  
**Storage**: JSON corpus/query files on disk (unchanged formats)  
**Testing**: `unittest` (constitution); repository may list optional pytest in dev extras—implementation verification should use the same runner the CI/README prescribes  
**Target Platform**: CLI / library usage on developer machines (macOS/Linux typical)  
**Project Type**: Python package with `src/services` CLI-backed flows  
**Performance Goals**: No regression vs. current O(n) two-pass corpus build; no extra copies beyond today’s lists/tuples  
**Constraints**: No new PyPI runtime deps; Google-style docstrings on all public API; domain errors via `ValidationError` / project hierarchy  
**Scale/Scope**: Single module (`dataset.py`) API surface change + import rewires in `runner.py`, `services/__init__.py`, and tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status |
|-----------|--------|
| I. Standard Library First | **Pass** — no new dependencies |
| II. Style, Typing, Functional-First | **Pass** — preserve type hints; small change surface |
| III. Memory and Algorithmic Efficiency | **Pass** — same algorithms and data shapes |
| IV. Documentation (Google Style) | **Pass** — add/refresh docstrings on newly public methods and class summary |
| V. Domain Errors | **Pass** — keep `ValidationError` paths unchanged |

**Post-design re-check**: Still pass; design is rename + call-site migration only.

## Project Structure

### Documentation (this feature)

```text
specs/20260413-202436-corpuses-public-api/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
│   └── corpus-api.md
└── tasks.md             # Phase 2 (/speckit.tasks) — not created here
```

### Source Code (repository root)

```text
src/
├── main.py
└── services/
    ├── __init__.py
    ├── args.py
    ├── dataset.py       # Corpuses + removal of module-level aliases
    ├── runner.py
    ├── jsonio.py
    └── ...

tests/
├── test_pipeline.py
├── test_jsonio.py
├── test_equivalence.py
├── test_scale_smoke.py
└── ...
```

**Structure Decision**: Single Python package under `src/services`; feature touches `dataset.py` and every file that imported removed module functions.

## Implementation approach (for /speckit.tasks)

1. **Rename** on `Corpuses`: `_degree_to_rank` → `degree_to_rank`, `_domain_to_index` → `domain_to_index`, `_raw_to_prevector` → `raw_to_prevector`, `_apply_minmax` → `apply_minmax`, `_compute_scaling_stats` → `compute_scaling_stats`, `_normalize_query_raw` → `normalize_query_raw`, `_build_normalized_pair` → `build_normalized_corpus` (classmethod; same return type as today’s private helper).
2. **Update** internal references (`from_raw`, `build_normalized_corpus` body, `normalize_query`, etc.) to call the new names (use `cls` / `Corpuses` consistently).
3. **Delete** module-level block: `degree_to_rank`, `domain_to_index`, `raw_to_prevector`, `apply_minmax`, `compute_scaling_stats`, `iter_synthetic_profiles`, `build_normalized_corpus`, `normalize_query_raw`, `load_corpus_from_path`, `get_synthetic_corpus`, `get_synthetic_query`.
4. **Migrate call sites**: `runner.py` → `Corpuses.iter_synthetic_profiles`; `test_*` → `Corpuses.*`; `services/__init__.py` → drop `build_normalized_corpus` export or replace with documenting `Corpuses.build_normalized_corpus` only in `__all__` if still desired (prefer **remove** from `__all__` and use `Corpuses` only to avoid duplicate public paths).
5. **Docstrings**: Class docstring must no longer say names starting with `_` are internal; each promoted method gets `Args` / `Returns` / `Raises` as needed.
6. **Verify**: Grep for removed symbol names; run full test suite.

## Complexity Tracking

> No constitution violations; table not required.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
