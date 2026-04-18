# Feature Specification: One-Hot Encoding for favourite_domain in RawProfile Normalization

**Feature Branch**: `20260418-123831-rawprofile-onehot-encoding`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "I want to change the logic in RawProfile when normalization. Now it apply label encoding all categorical variable (highest_degree and favourite_domain) but favourite_domain is nominal category --> we should apply onehot encoding instead"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Normalize corpus with one-hot domain encoding (Priority: P1)

A developer builds or loads a corpus of raw profiles. The normalization pipeline encodes `highest_degree` with its existing ordinal (label) encoding, but encodes `favourite_domain` as a one-hot vector instead of a single numeric index. The resulting normalized vectors have a larger, consistent dimensionality that correctly represents the nominal nature of the domain field.

**Why this priority**: This is the core correctness fix — label encoding on a nominal variable introduces a false ordinal relationship between domains (e.g. implying "data_science" > "software"), which distorts all distance calculations downstream.

**Independent Test**: Build a corpus from raw profiles covering all `favourite_domain` values; verify each normalized vector has the correct expanded dimension, that each domain slot is 0 or 1, and that exactly one slot is 1 per profile.

**Acceptance Scenarios**:

1. **Given** a `RawProfile` with `favourite_domain = "software"` (first in catalog), **When** normalized, **Then** the domain segment of the vector has `1.0` at the first domain position and `0.0` at all other domain positions.
2. **Given** a `RawProfile` with `favourite_domain = "research"` (eighth in catalog), **When** normalized, **Then** the domain segment has `1.0` at the eighth domain position and `0.0` elsewhere.
3. **Given** a full corpus of raw profiles, **When** `build_normalized_corpus` runs, **Then** every resulting normalized vector has 14 dimensions total (4 numeric features + 10 one-hot domain dimensions).
4. **Given** a `favourite_domain` value not present in the domain catalog, **When** encoding is attempted, **Then** a validation error is raised, consistent with existing behavior.

---

### User Story 2 - Query normalization aligned to new vector shape (Priority: P2)

A developer submits a query `RawProfile` for similarity search. The query is normalized using the same one-hot scheme so its vector aligns dimensionally with the corpus vectors.

**Why this priority**: If the query vector uses a different encoding than the corpus, all distance calculations are wrong. Consistency between corpus and query encoding is mandatory for correct search results.

**Independent Test**: Normalize a query profile; verify the resulting vector has 14 dimensions with the domain one-hot segment populated correctly.

**Acceptance Scenarios**:

1. **Given** a query `RawProfile` with `favourite_domain = "finance"`, **When** query normalization is applied, **Then** the returned vector has 14 dimensions with `1.0` in the "finance" slot and `0.0` in all other domain positions.
2. **Given** corpus scaling stats computed under the new encoding, **When** a query is normalized with those stats, **Then** the four numeric dimensions (age, income, degree rank, learning hours) are Min–Max scaled using the stats, and the domain segment is one-hot with no Min–Max scaling applied to the binary bits.

---

### User Story 3 - Query weights aligned to new dimensionality (Priority: P3)

A developer specifies per-dimension weights in a query configuration. The weights must account for the expanded 14-dimension vector so that individual domain slots can each be weighted independently.

**Why this priority**: Once the vector expands, query configs with only 5 weight entries become invalid. This boundary must produce a clear error rather than silent incorrect distance calculations.

**Independent Test**: Load a query config with 14 weights; verify it is accepted and each weight maps to the correct vector dimension.

**Acceptance Scenarios**:

1. **Given** a query config with 14 weight values, **When** loaded, **Then** all weights are applied to the corresponding vector dimensions without error.
2. **Given** a query config with 5 weight values (old format), **When** loaded, **Then** a clear error is produced rather than silently computing incorrect distances.

---

### Edge Cases

- What happens when a corpus contains profiles all sharing the same `favourite_domain`? (All 1s in one column; Min–Max scaling must not be applied to one-hot bits, so values stay at exactly `1.0` or `0.0`.)
- How does the system behave when `favourite_domain` is `None` or an empty string in a `RawProfile`?
- What happens when `ScalingStats` built under the old 5-dimension layout is used with a vector produced under the new 14-dimension layout?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The normalization pipeline MUST encode `favourite_domain` as a one-hot binary vector with one dimension per catalog entry (10 dimensions for the current 10-entry domain catalog).
- **FR-002**: The normalization pipeline MUST continue to encode `highest_degree` using its existing ordinal mapping, unchanged.
- **FR-003**: The normalized profile vector MUST have a total of 14 dimensions ordered as: `[age, monthly_income, degree_rank, daily_learning_hours, domain_0, domain_1, …, domain_9]`.
- **FR-004**: The vector dimension constant MUST be updated to reflect the new total dimensionality of 14.
- **FR-005**: The `ProfileVector` type alias, `ScalingStats`, and `NormalizedProfile.vector` definitions MUST be updated to represent 14-dimensional vectors.
- **FR-006**: Min–Max scaling MUST be applied only to the four numeric features; the 10 one-hot domain dimensions MUST NOT be Min–Max scaled (they are already bounded to {0, 1}).
- **FR-007**: Query normalization MUST produce vectors using the same one-hot encoding so query vectors are dimensionally compatible with corpus vectors.
- **FR-008**: The system MUST raise a validation error when `favourite_domain` is not present in the domain catalog, consistent with existing error-handling behavior.
- **FR-009**: The query weight keys definition MUST be updated to enumerate all 14 dimension keys (4 numeric + 10 domain slots) so query JSON parsing remains consistent.
- **FR-010**: Distance computation and search strategies MUST continue to function correctly with the new dimensionality without changes to their core algorithms.

### Key Entities

- **RawProfile**: Unchanged input record; `favourite_domain` remains a plain string field.
- **NormalizedProfile**: Output record; `vector` expands from 5 to 14 float dimensions.
- **ScalingStats**: Stores per-dimension min/max; expands from 5-entry to 14-entry tuples; one-hot domain slots hold placeholder values (min=0, max=1) to keep the structure uniform.
- **ProfileVector**: Type alias for the normalized feature vector; must represent 14 floats.
- **DOMAIN_CATALOG**: 10-entry ordered tuple; its ordering defines which index each domain occupies in the one-hot segment.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any valid `RawProfile`, the domain one-hot segment of its normalized vector has exactly one `1.0` and nine `0.0` values, verified across all 10 catalog domains.
- **SC-002**: All existing normalization and search tests pass without regression in the four numeric dimensions (age, income, degree, learning hours).
- **SC-003**: A corpus of 10,000 profiles normalizes without errors, with every resulting vector having exactly 14 dimensions.
- **SC-004**: Query vectors produced by query normalization are dimensionally compatible with corpus vectors for all 10 `favourite_domain` catalog values.
- **SC-005**: Distance-based search results correctly treat two profiles with different `favourite_domain` values as having maximum domain distance (no false ordinal proximity introduced by the old encoding).

## Assumptions

- The domain catalog tuple is the single source of truth for one-hot dimension ordering; adding or removing catalog entries changes vector dimensionality and invalidates existing serialized corpora.
- Min–Max scaling is intentionally skipped for one-hot bits because they are already in {0, 1}; `ScalingStats` stores placeholder (min=0, max=1) for those 10 slots to keep the structure uniform.
- Existing serialized corpus JSON files will be invalidated by this change and must be regenerated; migration of old files is out of scope.
- The four numeric features retain their current positions at the start of the vector (indices 0–3); the 10 domain one-hot slots occupy indices 4–13.
- Search strategy implementations iterate over vector dimensions generically and do not hard-code dimension count, so they adapt once the dimension constant and vector types are updated.
