# Tasks: Benchmark All Cases — KD-tree vs Baseline

**Input**: Design documents from `specs/20260501-143010-benchmark-all-cases/`  
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or disjoint code blocks, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Path Conventions

All source changes are confined to a single project at the repository root:

```
src/services/menu.py       — all new logic added here
tests/test_benchmark_all_cases.py  — new test file (Polish phase)
```

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Add the shared constants and input helpers that both user stories depend on. No user story tasks can begin until this phase is complete.

**⚠️ CRITICAL**: Phases 3 and 4 both depend on these primitives.

- [x] T001 Add `_WEIGHT_SCENARIOS` module-level constant to `src/services/menu.py` — a list of 4 dicts, each with `"label": str` and `"weights": tuple[float, ...]` (9-dimensional, QUERY_WEIGHT_KEYS order): Uniform `(1,1,1,1,1,1,1,1,1)`, Domain-heavy `(1,1,1,1,5,5,5,5,5)`, Degree-heavy `(1,1,1,5,1,1,1,1,1)`, Income-heavy `(1,5,1,1,1,1,1,1,1)`
- [x] T002 Add `_input_int_list(prompt: str) -> list[int]` helper to `src/services/menu.py` — reads a comma-separated string, strips whitespace, validates each token is a positive integer, deduplicates and sorts the result, reprompts on invalid input
- [x] T003 Add `_find_or_generate_dataset_for_size(size: int) -> Path | None` helper to `src/services/menu.py` — scans `.rmit/dataset/*/metadata.txt` for a line `N=<size>`, returns the corresponding `profiles.json` path if found; otherwise calls `run_generate_corpus(size, seed=42)` then rescans; returns `None` only if generation fails

**Checkpoint**: Foundation ready — US1 and US2 implementation can begin.

---

## Phase 2: User Story 1 — Run Full Benchmark Suite from Menu (Priority: P1) 🎯 MVP

**Goal**: A user selects option 5 from the menu, provides dataset sizes and k values, and receives a four-section report (effect of dataset size, k value, attribute weights, and correctness verification) without any additional per-query prompts.

**Independent Test**: Launch the menu, select option 5, enter `"10000"` for sizes and `"2,5"` for k values, verify that the four report sections print without error and the menu returns to the main prompt. Requires no pre-existing dataset (the option generates one automatically).

### Implementation for User Story 1

- [x] T004 [US1] Add `_run_case(baseline, kdtree, corpuses, profile_dict: dict, weights: tuple[float, ...], k: int) -> dict` helper to `src/services/menu.py` — builds `VectorizedQueryProfile` directly via `corpuses.normalize_query(QProfile(**profile_dict))` (no temp file), calls `get_topk` for both strategies, compares `profile_ids` for exact equality and `distances` within `HITS_EQUAL_ABS_TOL`, returns a `CaseRecord` dict with keys `b_search`, `k_search`, `speedup` (`b_search/k_search` guarded against zero division), `correct` (bool)
- [x] T005 [US1] Add `_do_benchmark_all_cases() -> None` action to `src/services/menu.py` — prompts for dataset sizes via `_input_int_list`, prompts for k values via `_input_int_list`, validates that no k value exceeds 20 (warn and cap), then for each size: calls `_find_or_generate_dataset_for_size`, loads `Corpuses.from_json_path`, calls `build_searcher` for both strategies (records build times), then runs: (a) Section 1 — for each size use first k, uniform weights, random profile from `_SAMPLE_PROFILES`; (b) Section 2 — for first size, each k, uniform weights, random profile; (c) Section 3 — for first size, first k, each of `_WEIGHT_SCENARIOS`, fixed first `_SAMPLE_PROFILES` entry; (d) Correctness — all (size, k, weight_scenario, random profile) combinations; collects all `CaseRecord` dicts and passes to `_print_all_cases_report`
- [x] T006 [US1] Add `_print_all_cases_report(size_rows: list[dict], k_rows: list[dict], weight_rows: list[dict], all_rows: list[dict]) -> None` to `src/services/menu.py` — renders a bordered console report with four labeled sections; Section 1 table columns: `Size | B Build (ms) | KD Build (ms) | B Search (ms) | KD Search (ms) | Speedup`; Section 2 table: `k | B Search (ms) | KD Search (ms) | Speedup`; Section 3 table: `Weight Scenario | B Search (ms) | KD Search (ms) | Speedup`; Section 4 correctness table: `Size | k | Weight | Profile | Match?` with `✓`/`✗` symbols and a summary line `"Correctness: X/Y cases passed"`
- [x] T007 [US1] Update `_MENU` string in `src/services/menu.py` — insert `"5. Run All Cases Benchmark: Baseline vs KD-tree"` before Exit and renumber Exit to `"6. Exit"`, update the prompt hint from `[1-5]` to `[1-6]`
- [x] T008 [US1] Update `interactive_menu()` in `src/services/menu.py` — add `"5": ("Run All Cases Benchmark", _do_benchmark_all_cases)` to `_ACTIONS`; change exit check from `choice == "5"` to `choice == "6"`; change prompt string to `"Enter option [1-6]: "` and invalid-choice message to `"please enter 1–6"`

**Checkpoint**: After T008 the new menu option is fully wired. Run `python src/main.py`, choose option 5, enter `10000` and `2` — verify a four-section report prints and the menu returns cleanly.

---

## Phase 3: User Story 2 — Aggregated Summary Statistics (Priority: P2)

**Goal**: After all cases run, a summary block appears showing average speedup, best-case (profile + k + weight label), and worst-case — enabling quick insight without reading every row.

**Independent Test**: After completing US1, run option 5 with at least 2 k values. Verify the summary block appears after Section 4 and its avg/best/worst values are numerically consistent with the per-row speedup values shown in Sections 1–3.

**Independent Test**: After completing Phase 2 (US1), extend `_print_all_cases_report` with the summary block and verify it renders correctly with known input.

### Implementation for User Story 2

- [x] T009 [US2] Extend `_print_all_cases_report()` in `src/services/menu.py` — after Section 4, compute summary statistics over `all_rows`: `avg_speedup = mean(r["speedup"] for r in all_rows)`, `best = max(all_rows, key=lambda r: r["speedup"])`, `worst = min(all_rows, key=lambda r: r["speedup"])`; print a summary block with avg speedup (2 decimal places), best-case row details (size, k, weight label, speedup), and worst-case row details; guard against empty `all_rows`; use only `statistics.mean` from stdlib or manual mean to avoid PyPI

**Checkpoint**: After T009 the summary block appears at the bottom of every all-cases report run. Verify that changing input parameters changes the reported best/worst cases accordingly.

---

## Phase 4: Polish & Tests

**Purpose**: Test coverage for all new helpers and the wired menu option.

- [x] T010 [P] Write `tests/test_benchmark_all_cases.py` — unit tests for `_input_int_list`: valid comma-separated input returns sorted deduplicated list; non-integer tokens cause reprompt (mock `input`); single value works; negative integers rejected; whitespace-padded tokens accepted
- [x] T011 [P] Add tests to `tests/test_benchmark_all_cases.py` for `_find_or_generate_dataset_for_size` — mock filesystem scan: found case returns correct path; not-found case calls `run_generate_corpus` and rescans; generation failure returns `None`
- [x] T012 [P] Add tests to `tests/test_benchmark_all_cases.py` for `_run_case` correctness flag — construct small in-memory `Corpuses` (5 profiles), run `_run_case` with known query; assert `correct=True` when both strategies return identical results; assert `correct=False` by monkey-patching KD-tree to return a wrong result
- [x] T013 Add smoke test to `tests/test_benchmark_all_cases.py` for the full report flow — generate a 500-profile corpus in a temp dir, build both strategies, construct minimal `size_rows`/`k_rows`/`weight_rows`/`all_rows` dicts, call `_print_all_cases_report` with captured stdout, assert all four section headers appear in output and the correctness summary line is present

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: No dependencies — start immediately
- **Phase 2 (US1)**: Depends on Phase 1 completion — T004 needs `_WEIGHT_SCENARIOS` and `VectorizedQueryProfile` imports; T005 needs T002, T003, T004
- **Phase 3 (US2)**: Depends on T006 existing (extends `_print_all_cases_report`)
- **Phase 4 (Polish)**: Depends on Phase 2 and Phase 3 completion

### User Story Dependencies

- **US1 (P1)**: After Phase 1 — no dependency on US2; independently testable at T008 checkpoint
- **US2 (P2)**: After T006 — extends the report renderer; independently testable by calling `_print_all_cases_report` with pre-built row dicts

### Within Each User Story (US1 execution order)

```
T001, T002, T003 (parallel) → T004 → T005 → T006, T007 (parallel) → T008
```

T005 depends on T002 (`_input_int_list`), T003 (`_find_or_generate_dataset_for_size`), T004 (`_run_case`).  
T006 and T007 can be added in parallel once T005 is complete.  
T008 wires everything — must be last in US1.

### Parallel Opportunities

```
# Phase 1 — all three foundational tasks touch disjoint parts of menu.py (add new names only):
T001 (_WEIGHT_SCENARIOS) ‖ T002 (_input_int_list) ‖ T003 (_find_or_generate_dataset_for_size)

# Phase 4 — all test tasks touch test_benchmark_all_cases.py but are independent test classes:
T010 ‖ T011 ‖ T012 (can be written simultaneously in separate test classes)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Foundational (T001–T003)
2. Complete Phase 2: US1 (T004–T008)
3. **STOP and VALIDATE**: Run `python src/main.py`, select option 5, verify four-section report prints
4. Option 5 is fully functional as MVP

### Incremental Delivery

1. Phase 1 + Phase 2 → Menu option 5 works end-to-end (MVP)
2. Phase 3 (T009) → Summary statistics appear; no behaviour regression on Phases 1–2
3. Phase 4 (T010–T013) → Test coverage added; no behaviour regression

---

## Notes

- All changes are confined to `src/services/menu.py` and the new `tests/test_benchmark_all_cases.py`
- No new imports beyond what menu.py already uses; `statistics.mean` (stdlib) is acceptable for T009 if computing mean
- `QProfile` must be imported in `_run_case` — it's already available via `services.dto` (check existing menu.py imports and add if missing)
- `HITS_EQUAL_ABS_TOL` must be imported from `services.constants` in `_run_case`
- `random.choice` is already available (stdlib); use for random profile selection in T005
- Guard all speedup calculations against `k_search == 0` (use `float("inf")` or a sentinel)
- Commit after each checkpoint validation
