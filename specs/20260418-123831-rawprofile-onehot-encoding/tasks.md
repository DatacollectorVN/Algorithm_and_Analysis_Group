# Tasks: One-Hot Encoding for favourite_domain in RawProfile Normalization

**Input**: Design documents from `/specs/20260418-123831-rawprofile-onehot-encoding/`  
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no interdependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single-project layout: `src/`, `tests/` at repository root.

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Pure type-annotation changes that unblock all downstream modifications. No runtime behavior changes — safe to land first.

**⚠️ CRITICAL**: All user-story phases depend on these type definitions being updated.

- [x] T001 Update `ProfileVector` type alias from `tuple[float, float, float, float, float]` to `tuple[float, ...]` in `src/services/dto/profiles.py`
- [x] T002 Update `ScalingStats` field types (`mins`, `maxs`) from `tuple[float, float, float, float, float]` to `tuple[float, ...]` in `src/services/dto/profiles.py`

**Checkpoint**: Type aliases updated — no runtime impact yet. User-story phases can now begin.

---

## Phase 2: User Story 1 — Normalize corpus with one-hot domain encoding (Priority: P1) 🎯 MVP

**Goal**: Replace label encoding of `favourite_domain` with a 10-bit one-hot encoding throughout the normalization pipeline so corpus vectors carry correct nominal representation.

**Independent Test**: Build a corpus from profiles covering all 10 `DOMAIN_CATALOG` entries; assert every `NormalizedProfile.vector` has length 14, the domain segment has exactly one `1.0` and nine `0.0` values, and `highest_degree` ordinal encoding is unchanged.

### Implementation for User Story 1

- [x] T003 [P] [US1] Add `domain_to_onehot(domain: str) -> tuple[float, ...]` to `src/services/dataset.py` — returns a 10-float one-hot tuple (1.0 at catalog index, 0.0 elsewhere); raise `ValidationError` on unknown domain; keep `domain_to_index` until T004 replaces its callers
- [x] T004 [US1] Update `raw_to_prevector` in `src/services/dataset.py` to call `domain_to_onehot` and return a 14-float tuple `(age, income, degree_rank, hours, d0, d1, …, d9)`; remove `domain_to_index` (no longer called)
- [x] T005 [US1] Update `apply_minmax` in `src/services/dataset.py` to apply Min–Max scaling only to indices 0–3 and pass indices 4–13 (one-hot domain bits) through unchanged
- [x] T006 [US1] Update `VECTOR_DIM` from `5` to `14` in `src/services/constants.py` — do this after T003–T005 so all 14-float producers are ready before the dimension constant changes
- [x] T007 [P] [US1] Refactor `bbox_of_point` in `src/services/helper.py` to return `tuple(v[i] for i in range(VECTOR_DIM))` (loop-based, typed as `ProfileVector`) instead of the hard-coded 5-index construction
- [x] T008 [P] [US1] Refactor `union_bbox` in `src/services/helper.py` to build `lo` and `hi` via `tuple(min(lo1[i], lo2[i]) for i in range(VECTOR_DIM))` and `tuple(max(...))` instead of explicit index [0]–[4] construction
- [x] T009 [P] [US1] Update `NormalizedProfile` docstring in `src/services/dto/profiles.py` — change `[0, 1]^5` to `[0, 1]^14` and update the `vector` field description
- [x] T010 [P] [US1] Update `src/services/dto/__init__.py` module docstring — change `[0, 1]^5` reference to `[0, 1]^14`
- [x] T011 [US1] Update `tests/test_pipeline.py`:
  - Expand all hard-coded 5-float tuples (pre-vectors, stats, normalized vectors) to 14-float equivalents
  - Fix `test_minmax_constant_dimension` and `test_raw_to_prevector_roundtrip_normalized` with 14-dim tuples
  - Add `TestOneHotEncoding` class with tests for: single-domain one-hot correctness for every catalog entry, mutual exclusivity (exactly one 1.0, nine 0.0), corpus with all profiles sharing one domain (no scaling collapse), and unknown domain raises `ValidationError`

**Checkpoint**: `python -m unittest tests/test_pipeline.py` must pass. User Story 1 is independently functional.

---

## Phase 3: User Story 2 — Query normalization aligned to new vector shape (Priority: P2)

**Goal**: Ensure `distance.py` and `helper.py` type contracts and error messages match the 14-dim vectors now produced by the updated normalization pipeline.

**Independent Test**: Call `normalize_query_raw` with a `RawProfile`; assert the returned vector has 14 elements and the domain one-hot segment is correct. Call `weighted_squared_distance` with two 14-dim vectors and verify it returns a finite non-negative float without error.

### Implementation for User Story 2

- [x] T012 [P] [US2] Update `weighted_squared_distance` and `_validate_weights` in `src/services/search/distance.py` — change parameter type hints from `tuple[float, float, float, float, float]` to `tuple[float, ...]`; update the `ValidationError` message from `"must have length 5"` to `f"must have length {VECTOR_DIM}"` (import `VECTOR_DIM` from `services.constants`)
- [x] T013 [P] [US2] Update `weighted_sq_dist_query_to_box` signature in `src/services/helper.py` — change `query`, `lo`, `hi`, `weights` parameter types from `ProfileVector` (5-tuple) to `ProfileVector` (now `tuple[float, ...]`); no logic change needed since the function already loops over `VECTOR_DIM`
- [x] T014 [US2] Update `tests/test_distance.py` — expand every 5-float literal tuple `(x, x, x, x, x)` to a 14-float equivalent `(x, x, x, x, x, x, x, x, x, x, x, x, x, x)` in all test methods; update any assertions that reference vector length

**Checkpoint**: `python -m unittest tests/test_distance.py` must pass. Query vectors align dimensionally with corpus vectors.

---

## Phase 4: User Story 3 — Query weights aligned to new dimensionality (Priority: P3)

**Goal**: Update the query JSON weight schema from 5 keys to 14 keys so per-dimension weights can be specified for each one-hot domain slot independently.

**Independent Test**: Write a query JSON with 14 weight keys (one per `QUERY_WEIGHT_KEYS` entry); load it with `load_query_json`; assert `len(weights) == 14` and the returned tuple maps to the correct dimensions.

### Implementation for User Story 3

- [x] T015 [US3] Update `QUERY_WEIGHT_KEYS` in `src/services/constants.py` to the 14-entry tuple: `("age", "monthly_income", "education", "daily_learning_hours", "domain_software", "domain_data_science", "domain_finance", "domain_healthcare", "domain_education", "domain_manufacturing", "domain_retail", "domain_research", "domain_design", "domain_operations")`
- [x] T016 [US3] Update `load_query_json` in `src/services/jsonio.py` — replace the hard-coded 5-element weights tuple construction `(weights_list[0], ..., weights_list[4])` with `tuple(weights_list)` so it adapts automatically to the 14-key `QUERY_WEIGHT_KEYS`; update return type hint from `tuple[float, float, float, float, float]` to `tuple[float, ...]`
- [x] T017 [US3] Update `tests/test_jsonio.py` — replace the 5-key `"weights"` dict (containing `"domain"`) with the 14-key dict matching new `QUERY_WEIGHT_KEYS`; update `self.assertEqual(len(weights), 5)` assertion to `len(weights) == 14`

**Checkpoint**: `python -m unittest tests/test_jsonio.py` must pass. Old 5-key query JSON produces a clear `ValidationError`.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Update remaining test fixtures that still reference 5-dim vectors; validate full suite.

- [x] T018 [P] Update `tests/test_baseline.py` — expand `NormalizedProfile` vector fixtures from `(x, x, x, x, x)` to 14-float equivalents; expand `self.w` weight tuple from 5 to 14 entries
- [x] T019 [P] Update `tests/test_kdtree.py` — expand all weight tuples and `NormalizedProfile` vector fixtures from 5-dim to 14-dim
- [x] T020 [P] Update `tests/test_scale_smoke.py` — expand `w = (1.0, 1.0, 1.0, 1.0, 1.0)` weight tuples (appears twice) to 14-entry equivalents `(1.0,) * 14`
- [x] T021 Run full test suite `python -m unittest discover tests` and confirm zero failures

**Checkpoint**: All tests green. Feature complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No runtime impact — start immediately
- **US1 (Phase 2)**: Depends on Phase 1 type changes. T003 can start in parallel with T001/T002. T006 (VECTOR_DIM) MUST wait for T003–T005.
- **US2 (Phase 3)**: Depends on Phase 2 completion (14-dim vectors must exist before distance tests make sense)
- **US3 (Phase 4)**: Depends on Phase 2 (VECTOR_DIM 14 needed) and independent of US2
- **Polish (Phase 5)**: Depends on US1 + US2 + US3 completion

### Within User Story 1

- T003 (add `domain_to_onehot`) → T004 (update `raw_to_prevector`) → T005 (update `apply_minmax`) → T006 (update `VECTOR_DIM`)
- T007 and T008 (`helper.py` refactors) can run in parallel with T003–T005 but T006 must complete before them (they depend on `VECTOR_DIM = 14`)
- T009, T010 (docstrings) are [P] — can run any time in Phase 2
- T011 (tests) must wait for T003–T010

### User Story Dependencies

- **User Story 1 (P1)**: Foundational phase complete → can begin
- **User Story 2 (P2)**: User Story 1 complete (needs 14-dim vectors to test against)
- **User Story 3 (P3)**: User Story 1 complete (needs `VECTOR_DIM = 14` in constants)
- **User Story 2 and 3**: Can proceed in parallel after US1

### Parallel Opportunities

- T001 and T002 can run in parallel (same file but disjoint edits to `profiles.py`)
- T003, T009, T010 are parallelizable once Foundational is done
- T007 and T008 are parallelizable (both in `helper.py` but disjoint functions)
- T012 and T013 are parallelizable (different files)
- T018, T019, T020 are parallelizable (different test files)

---

## Parallel Example: User Story 1

```
# Parallelizable start — once Foundational done:
Task T003: Add domain_to_onehot in src/services/dataset.py
Task T009: Update NormalizedProfile docstring in src/services/dto/profiles.py
Task T010: Update dto/__init__.py docstring

# Then sequentially:
Task T004: Update raw_to_prevector (depends on T003)
Task T005: Update apply_minmax (depends on T004)
Task T006: Update VECTOR_DIM to 14 (depends on T003–T005)

# Parallelizable once T006 done:
Task T007: Refactor bbox_of_point in src/services/helper.py
Task T008: Refactor union_bbox in src/services/helper.py

# Finally:
Task T011: Update tests/test_pipeline.py (depends on all above)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Foundational (type aliases — no risk)
2. Complete Phase 2: User Story 1 (encoding + VECTOR_DIM + helper refactors)
3. **STOP and VALIDATE**: `python -m unittest tests/test_pipeline.py`
4. Corpus normalization now produces correct 14-dim one-hot vectors

### Incremental Delivery

1. Phase 1 (Foundational) → safe to merge immediately
2. Phase 2 (US1) → corpus + helper correct; run `test_pipeline.py`
3. Phase 3 (US2) → distance layer aligned; run `test_distance.py`
4. Phase 4 (US3) → query JSON aligned; run `test_jsonio.py`
5. Phase 5 (Polish) → all other test fixtures updated; full suite green

---

## Notes

- [P] tasks operate on different files or disjoint sections — safe to parallelize
- [Story] label maps each task to a specific user story for traceability
- **T006 (VECTOR_DIM update) is the critical atomic moment**: complete T003–T005 first so all 14-float producers are ready before the runtime constant changes
- Old query JSON files with 5 weight keys will produce `ValidationError` after T015–T016 — this is the expected and documented behavior (migration out of scope per spec Assumptions)
- `compute_scaling_stats` in `dataset.py` already loops with `VECTOR_DIM` — no logic change needed, it adapts automatically once `VECTOR_DIM = 14` and receives 14-float pre-vectors
