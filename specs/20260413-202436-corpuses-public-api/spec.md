# Feature Specification: Corpus pipeline public API

**Feature Branch**: `20260413-202436-corpuses-public-api`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: User description: "Please construct the Corpuses class here to change the private mehtod to public method"

## Overview

Maintainers of the profile-search exercise need a stable, documented way to reuse the steps that turn raw profile records into comparable numeric vectors and to align new queries with an existing corpus. Some of those steps are currently treated as internal-only, which makes custom tests and teaching extensions harder to keep correct. This feature promotes those steps to a clear, supported contract so integrators no longer depend on undocumented entry points.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Use documented corpus steps (Priority: P1)

A developer integrating or extending the profile search pipeline needs to run individual steps—turning raw profiles into numeric features, computing scaling bounds, applying scaling, and normalizing queries—without depending on entry points that are explicitly reserved for internal use.

**Why this priority**: Without a clear public contract, every reuse risks breakage when internals change and slows onboarding for anyone customizing or testing the pipeline.

**Independent Test**: From documentation alone, a developer can invoke each discrete step in isolation on sample data and observe the same outcomes as when running the full end-to-end corpus build.

**Acceptance Scenarios**:

1. **Given** a valid raw profile record, **When** the developer applies the public encoding step, **Then** they obtain the same numeric feature tuple as produced by the full corpus build path for that record.
2. **Given** a non-empty set of encoded feature rows, **When** the developer computes scaling bounds via the public API, **Then** the resulting bounds match those used when building a corpus from the same raw set.
3. **Given** a query record and scaling bounds from an existing corpus, **When** the developer normalizes the query via the public API, **Then** the normalized vector matches the result of the existing query-normalization flow.

---

### User Story 2 - Stable consumption for wrappers and tests (Priority: P2)

Maintainers who already call thin module-level helpers want those helpers to remain valid, or to delegate to the same officially supported operations on the corpus bundle type, so tests and scripts do not silently depend on “private” class entry points.

**Why this priority**: Reduces duplicate definitions and clarifies a single source of truth for pipeline semantics.

**Independent Test**: Existing call sites that used supported module-level helpers continue to work; any call site that previously reached for internal-only class entry points can be updated to an equivalent public operation without behavior change.

**Acceptance Scenarios**:

1. **Given** a script that builds a corpus through the established public module helpers, **When** the feature is delivered, **Then** the script requires no behavioral change for valid inputs.
2. **Given** a test that needs only scaling statistics over pre-encoded rows, **When** it uses the promoted public operation on the corpus bundle type, **Then** results match the prior internal implementation for the same inputs.

---

### User Story 3 - Clear documentation of the contract (Priority: P3)

Readers of the project reference can see which operations are part of the supported corpus API versus experimental or internal details.

**Why this priority**: Prevents accidental coupling and sets expectations for future refactors.

**Independent Test**: A short “corpus API” summary exists that lists encoding, stats, per-vector scaling, full corpus assembly, and query normalization as supported operations.

**Acceptance Scenarios**:

1. **Given** the published reference for the corpus bundle type, **When** a new contributor reads it, **Then** they can name each major pipeline stage and how to invoke it through supported entry points.

---

### Edge Cases

- Empty raw corpus: building scaling statistics or a full corpus must fail with a clear, explicit error (no partial or silent success).
- Unknown categorical values (e.g. degree or domain not in the catalog): encoding must fail with a message that identifies the invalid value.
- Single-row corpus: min–max scaling must still produce well-defined bounds and normalized output consistent with min=max dimensions where applicable.
- Query normalization when bounds are degenerate (min equals max on a dimension): behavior must remain defined and consistent with current rules (e.g. same handling as today).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The corpus bundle type MUST expose, as part of its supported public contract, discrete operations for: mapping catalog-backed categorical fields to numeric ranks, converting a raw profile to a fixed-size numeric feature tuple before scaling, computing min–max scaling bounds over a collection of such tuples, applying those bounds to normalize one tuple, assembling a normalized corpus (profiles plus bounds) from a sequence of raw profiles, and normalizing a single raw query against given bounds.
- **FR-002**: For valid inputs, each public operation MUST produce the same numeric results and structured outputs as the implementation used today by the end-to-end corpus and query paths.
- **FR-003**: For invalid inputs called out in edge cases, the system MUST fail with explicit, bounded errors (no undefined outputs), consistent with current behavior.
- **FR-004**: Existing supported flows for loading corpus data from files, generating synthetic corpora, and loading plus normalizing queries MUST remain behaviorally equivalent for valid inputs without requiring callers to adopt the newly promoted operations.
- **FR-005**: Published reference material for the corpus bundle type MUST describe the promoted operations as supported and MUST NOT describe them as internal-only building blocks.

### Key Entities

- **Raw profile**: A record with demographic and preference fields used before normalization.
- **Numeric feature tuple**: Fixed-length vector derived from a raw profile prior to min–max scaling.
- **Scaling bounds**: Per-dimension minimum and maximum values derived from a corpus of numeric feature tuples.
- **Normalized profile**: Identifier plus scaled feature tuple in the unit hypercube (or project-defined normalized space).
- **Corpus bundle**: Normalized collection together with the scaling bounds used to align queries.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new contributor can list all supported discrete corpus operations (encode, bounds, scale one row, build corpus, normalize query) from reference documentation alone, without inspecting non-documented code paths.
- **SC-002**: All existing automated tests for corpus construction, file load, and search-related flows pass without loosening assertions (updates limited to replacing calls to former internal-only entry points with the new public equivalents, if any tests relied on those).
- **SC-003**: For three representative cases (valid small corpus, empty corpus, invalid categorical value), documented expectations for success or failure match observed behavior in 100% of trials.

## Assumptions

- Primary consumers are developers and maintainers of this codebase (course tooling, experiments, and tests), not anonymous end users.
- On-disk JSON shapes and CLI user-visible behavior for `search` and related commands are unchanged unless a separate feature specifies otherwise.
- Module-level convenience functions may continue to exist and delegate to the corpus bundle type’s public operations; removing them is out of scope unless explicitly requested later.
- “Public” means documented and intended for use by integrators; it does not require exposing every helper used only for implementation convenience if redundant with a clearer public name.
