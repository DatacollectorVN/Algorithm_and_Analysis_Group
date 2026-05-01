# Feature Specification: Benchmark All Cases — KD-tree vs Baseline

**Feature Branch**: `20260501-143010-benchmark-all-cases`  
**Created**: 2026-05-01  
**Status**: Draft  
**Input**: User description: "I want to enhance the logic in that code (not need to create the new branch); I want to add new option in the current menu options to run all cases in benchmark KD-tree vs Baseline"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Full Benchmark Suite from Menu (Priority: P1)

A user opens the interactive menu and selects the new "Run All Cases" benchmark option. The system automatically runs both the Baseline and KD-tree strategies against every predefined sample profile and a representative set of k values, then displays a consolidated comparison report — without requiring any per-query input from the user.

**Why this priority**: This is the core capability being added. It eliminates manual repetition when a user wants to see how the two strategies compare across all scenarios rather than a single handpicked query.

**Independent Test**: Can be fully tested by selecting the new menu option with a generated dataset and verifying that results for all sample profiles and all k values are displayed without any additional user prompts.

**Acceptance Scenarios**:

1. **Given** a dataset has been generated and the menu is displayed, **When** the user selects the "Run All Cases" benchmark option, **Then** the system runs both strategies for every sample profile and every predefined k value and prints a structured results table.
2. **Given** no dataset exists, **When** the user selects the "Run All Cases" option, **Then** the system informs the user that a dataset must be generated first and returns to the menu.
3. **Given** the benchmark completes successfully, **When** results are displayed, **Then** each row shows the sample profile name, k value, Baseline search time, KD-tree search time, and the speedup multiplier.

---

### User Story 2 - View Aggregated Summary Statistics (Priority: P2)

After all cases are run, the user sees a summary section that aggregates the results — showing average speedup, the case where KD-tree performed best, and the case where it performed worst — so they can quickly judge overall algorithmic advantage.

**Why this priority**: Seeing individual rows is valuable, but a summary enables faster insight. This elevates the benchmark from a data dump to an analytical report.

**Independent Test**: Can be tested independently by verifying the summary block appears after the full results table and contains min, max, and average speedup values computed from the per-case results.

**Acceptance Scenarios**:

1. **Given** all cases have been benchmarked, **When** the results are displayed, **Then** a summary section shows average speedup, best-case speedup (with profile/k), and worst-case speedup (with profile/k).
2. **Given** all speedup values are computed, **When** the summary renders, **Then** values are rounded to a consistent number of decimal places and labeled clearly.

---

### Edge Cases

- What happens when the dataset has zero profiles (empty corpus)? → System should report that no data is available and skip the run.
- How does the system handle a k value larger than the number of profiles in the dataset? → It should cap k at the dataset size or skip that k value with a notice.
- What if strategy construction fails for one strategy but not the other? → Display results only for the successful strategy and show an error notice for the failed one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The interactive menu MUST expose a new numbered option labeled "Run All Cases Benchmark: Baseline vs KD-tree" (or similar clear label) alongside existing options.
- **FR-002**: When triggered, the system MUST iterate over all predefined sample profiles (the same set used in the single-query benchmark option) and a predefined set of k values (e.g., 1, 5, 10, 20) without prompting the user for each combination.
- **FR-003**: The system MUST build both strategies once per run and reuse them across all (profile, k) combinations to ensure fair and efficient comparison.
- **FR-004**: The system MUST display per-case results showing: sample profile identifier, k value, Baseline search time, KD-tree search time, and computed speedup factor.
- **FR-005**: The system MUST display an aggregated summary after all cases, including average speedup, best-case (profile + k with highest speedup), and worst-case (profile + k with lowest speedup).
- **FR-006**: If no dataset exists when the option is selected, the system MUST notify the user and return to the menu without crashing.
- **FR-007**: The new menu option MUST appear before the "Exit" option and integrate consistently with the existing menu numbering scheme.

### Key Entities

- **Sample Profile**: A predefined query profile (age, degree, domain, etc.) already defined in the menu; used as a benchmark query input.
- **k Value**: The number of top results to retrieve; a small fixed set of representative values is used (e.g., [1, 5, 10, 20]).
- **Benchmark Case**: A single (sample profile, k) combination; the unit of work in the all-cases run.
- **Speedup Factor**: KD-tree search time divided into Baseline search time; values > 1 indicate KD-tree is faster.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The new menu option is reachable and executes without errors on a dataset of at least 10,000 profiles within 60 seconds for the full suite of predefined cases.
- **SC-002**: Results are displayed for 100% of (sample profile × k value) combinations without requiring additional user interaction after option selection.
- **SC-003**: The aggregated summary values (average, best, worst speedup) are numerically consistent with the individual per-case results shown in the table.
- **SC-004**: The menu remains fully navigable after the benchmark completes — the user can immediately select any other option without restarting.

## Assumptions

- The predefined sample profiles and k values are fixed at development time; users are not expected to customize this set through the menu (they can still use option 2/3 for ad-hoc queries).
- Both strategies are built fresh each time the "Run All Cases" option is invoked (no `.pkl` cache reuse), ensuring consistent and fair timing.
- The existing dataset generation (option 1) is a prerequisite; the feature does not trigger dataset generation automatically.
- "All cases" is scoped to the 5 existing predefined sample profiles and a small representative set of k values — not every possible profile or every k from 1 to n.
- Build time is measured once per strategy per run and shown in the summary (not repeated per case), since building is shared across all cases.
