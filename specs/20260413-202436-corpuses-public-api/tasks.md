---
description: "Task list for Corpus pipeline public API (Corpuses + remove dataset aliases)"
---

# Tasks: Corpus pipeline public API

**Input**: Design documents from `/specs/20260413-202436-corpuses-public-api/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/corpus-api.md](./contracts/corpus-api.md), [quickstart.md](./quickstart.md)

**Tests**: Success criteria (spec SC-002) require existing tests to pass after migration; no separate TDD-only tasks (spec does not mandate test-first).

**Organization**: Phases follow user-story priorities from [spec.md](./spec.md); call-site migration (US2) can proceed in parallel with docstring work (US1) once core `dataset.py` refactor (Foundational) lands.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: User story label ([US1], [US2], [US3]) on story-phase tasks only
- Paths are relative to repository root unless noted

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm design artifacts before code changes

- [x] T001 Read [plan.md](./plan.md) and note rename map and files to touch under `src/services/` and `tests/`
- [x] T002 [P] Skim [spec.md](./spec.md) user stories (P1–P3), [research.md](./research.md) decisions, [data-model.md](./data-model.md), [quickstart.md](./quickstart.md), and [contracts/corpus-api.md](./contracts/corpus-api.md) for acceptance wording

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `Corpuses` exposes public static/class methods and module-level aliases are removed—required before meaningful imports elsewhere

**⚠️ CRITICAL**: No user-story checkpoint is valid until **T003** completes (package may not import cleanly in tests until **US2** tasks also finish)

- [x] T003 Promote `Corpuses` helpers to public names (`_degree_to_rank` → `degree_to_rank`, `_domain_to_index` → `domain_to_index`, `_raw_to_prevector` → `raw_to_prevector`, `_apply_minmax` → `apply_minmax`, `_compute_scaling_stats` → `compute_scaling_stats`, `_normalize_query_raw` → `normalize_query_raw`, `_build_normalized_pair` → `build_normalized_corpus`), update all internal `cls`/`Corpuses` references, and delete the module-level function block at the end of `src/services/dataset.py` (including `load_corpus_from_path`, `get_synthetic_corpus`, `get_synthetic_query`)

**Checkpoint**: `src/services/dataset.py` compiles; internal `from_raw` / `normalize_query` / `iter_synthetic_profiles` paths call the new public names

---

## Phase 3: User Story 1 - Use documented corpus steps (Priority: P1) 🎯 MVP

**Goal**: Public pipeline operations on `Corpuses` are documented as supported (spec FR-001, FR-005; plan docstring requirements)

**Independent Test**: From docstrings on `Corpuses` and its methods in `src/services/dataset.py`, a reader can identify encode → stats → scale → build corpus → normalize query without referring to underscore-prefixed helpers

### Implementation for User Story 1

- [x] T004 [P] [US1] Add or refresh Google-style docstrings (summary, `Args`, `Returns`, `Raises` where applicable) on class `Corpuses` and on `degree_to_rank`, `domain_to_index`, `raw_to_prevector`, `apply_minmax`, `compute_scaling_stats`, `build_normalized_corpus`, `normalize_query_raw`, `iter_synthetic_profiles`, and existing factories/instance methods as needed in `src/services/dataset.py`; replace class docstring language that claims `_`-prefixed names are the only internal building blocks

**Checkpoint**: User Story 1 satisfied when T003 + T004 are done

---

## Phase 4: User Story 2 - Stable consumption for wrappers and tests (Priority: P2)

**Goal**: All in-repo callers use `Corpuses` methods directly; no imports of removed module functions (spec FR-002–FR-004)

**Independent Test**: `python -m unittest discover` (or the repo’s documented test command) passes with zero references to deleted `dataset` module functions

### Implementation for User Story 2

- [x] T005 [P] [US2] Change `src/services/runner.py` to use `Corpuses.iter_synthetic_profiles` and drop `iter_synthetic_profiles` import from `services.dataset`
- [x] T006 [P] [US2] Remove `build_normalized_corpus` import and `__all__` entry from `src/services/__init__.py`; keep exporting `Corpuses` and other symbols unchanged
- [x] T007 [P] [US2] Update `tests/test_pipeline.py` to import and call `Corpuses` static methods (`degree_to_rank`, `domain_to_index`, `compute_scaling_stats`, `apply_minmax`, `iter_synthetic_profiles`, `raw_to_prevector`, `build_normalized_corpus`) instead of module-level functions
- [x] T008 [P] [US2] Update `tests/test_jsonio.py` to use `Corpuses.build_normalized_corpus` and `Corpuses.normalize_query_raw` instead of module-level imports
- [x] T009 [P] [US2] Update `tests/test_equivalence.py` to use `Corpuses.iter_synthetic_profiles` instead of module-level `iter_synthetic_profiles`
- [x] T010 [P] [US2] Update `tests/test_scale_smoke.py` to use `Corpuses.iter_synthetic_profiles` instead of module-level `iter_synthetic_profiles`

**Checkpoint**: User Stories 1 and 2 both satisfied when T003–T010 and T004 are done

---

## Phase 5: User Story 3 - Clear documentation of the contract (Priority: P3)

**Goal**: Tracked contract docs stay aligned with code; user-facing docs do not reference removed helpers (spec FR-005, US3)

**Independent Test**: [contracts/corpus-api.md](./contracts/corpus-api.md) matches `Corpuses` public surface; `README.md` contains no stale imports of removed `dataset` functions

### Implementation for User Story 3

- [x] T011 [US3] Reconcile `specs/20260413-202436-corpuses-public-api/contracts/corpus-api.md` with the final public method list and signatures in `src/services/dataset.py` (edit contract file if anything drifted during implementation)
- [x] T012 [P] [US3] Search `README.md` (and `docs/` if present) for references to removed module helpers (`degree_to_rank`, `get_synthetic_corpus`, etc.); update text to `Corpuses` usage or remove stale examples

**Checkpoint**: User Story 3 satisfied when T011–T012 are done

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Repo-wide consistency and verification

- [x] T013 [P] Run ripgrep from repository root for removed symbols (`^def (degree_to_rank|domain_to_index|raw_to_prevector|apply_minmax|compute_scaling_stats|iter_synthetic_profiles|build_normalized_corpus|normalize_query_raw|load_corpus_from_path|get_synthetic_corpus|get_synthetic_query)` in `src/` and `tests/`, and `from services.dataset import` lines listing those names); fix any stragglers
- [x] T014 Execute the full test suite using the project’s standard command (e.g. `python -m unittest discover -s tests -p 'test_*.py'` with `PYTHONPATH=src` if that is how CI runs) and confirm green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001, T002 — no code dependencies
- **Foundational (Phase 2)**: T003 — **blocks** all implementation that assumes new `Corpuses` names and removed aliases
- **User Story 1 (Phase 3)**: T004 depends on T003
- **User Story 2 (Phase 4)**: T005–T010 depend on T003 (not on T004)
- **User Story 3 (Phase 5)**: T011–T012 depend on T003–T010 (contract/README should reflect final code)
- **Polish (Phase 6)**: T013–T014 depend on T003–T012 for meaningful verification

### User Story Dependencies

- **US1 (P1)**: After T003; T004 completes the story
- **US2 (P2)**: After T003; T005–T010 complete the story (tests pass at T014)
- **US3 (P3)**: After code and tests stabilize (T003–T010, ideally T004 too)

### Parallel Opportunities

- **After T003**: T004 (US1, `dataset.py` docstrings) can run in parallel with T005–T010 (US2, other files)
- **After T003**: T005, T006, T007, T008, T009, T010 are parallelizable with each other (distinct files)
- **After US2**: T011 and T012 can run in parallel (contract vs `README.md`)
- **Polish**: T013 can run before or in parallel with final T014 (T014 should be last for green suite)

---

## Parallel Example: After T003 (US1 + US2)

```bash
# Story 1 (documentation on Corpuses):
Task T004: Google-style docstrings in src/services/dataset.py

# Story 2 (call sites — run together):
Task T005: src/services/runner.py
Task T006: src/services/__init__.py
Task T007: tests/test_pipeline.py
Task T008: tests/test_jsonio.py
Task T009: tests/test_equivalence.py
Task T010: tests/test_scale_smoke.py
```

---

## Parallel Example: User Story 3

```bash
Task T011: specs/20260413-202436-corpuses-public-api/contracts/corpus-api.md
Task T012: README.md (and docs/ if applicable)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1 (T001–T002) and Phase 2 (T003)
2. Complete Phase 3 (T004) — documented public `Corpuses` pipeline
3. **STOP and VALIDATE**: Read `src/services/dataset.py` docstrings against [contracts/corpus-api.md](./contracts/corpus-api.md)

### Incremental Delivery

1. T003 → codebase compiles; imports outside `dataset.py` still broken until US2
2. T004 + T005–T010 → full package + tests aligned
3. T011–T012 → contract and README aligned
4. T013–T014 → grep cleanup and green suite

### Suggested full-sequence (single developer)

`T001 → T002 → T003 → (T004 ∥ T005–T010) → T011 → T012 → T013 → T014`

---

## Task Summary

| Phase | Task IDs | Count |
|-------|-----------|-------|
| Setup | T001–T002 | 2 |
| Foundational | T003 | 1 |
| US1 | T004 | 1 |
| US2 | T005–T010 | 6 |
| US3 | T011–T012 | 2 |
| Polish | T013–T014 | 2 |
| **Total** | **T001–T014** | **14** |

| User story | Task IDs | Count |
|------------|----------|-------|
| US1 | T004 | 1 |
| US2 | T005–T010 | 6 |
| US3 | T011–T012 | 2 |

**Format validation**: Every task uses `- [ ]`, sequential `T###` ID, optional `[P]` where noted, `[US#]` only on story phases (T004–T012), and includes an explicit file path in the description.

---

## Notes

- Files that import only `Corpuses` (`src/services/search/**/*.py`, some tests) may need **no** edits; confirm with T013
- If CI uses a different test invocation than `unittest`, follow `.github/workflows` or `README.md` for T014
