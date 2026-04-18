# Research: One-Hot Encoding for favourite_domain

**Branch**: `20260418-123831-rawprofile-onehot-encoding`  
**Phase**: 0 — Pre-Design Research  
**Date**: 2026-04-18

---

## Decision 1: ProfileVector type representation at 14 dimensions

**Decision**: Change `ProfileVector` from `tuple[float, float, float, float, float]` (explicit 5-tuple) to `tuple[float, ...]` (variable-length homogeneous tuple).

**Rationale**: Explicitly listing 14 float annotations (`tuple[float, float, ..., float]`) is syntactically valid but creates maintenance burden — any future dimension change requires counting and updating 14 positions. The PEP 484 / PEP 695 recommended form for a homogeneous tuple of any length is `tuple[float, ...]`. Runtime enforcement is provided by `VECTOR_DIM` checks in `distance.py` and `weighted_sq_dist_query_to_box`.

**Alternatives considered**:
- Explicit 14-float annotation: rejected — verbose, fragile to future changes.
- `list[float]`: rejected — loses the immutable semantics that `frozen=True` dataclasses and `tuple` provide; incompatible with existing unpack operations.

---

## Decision 2: One-hot encoding representation

**Decision**: Encode `favourite_domain` as 10 float values (0.0 or 1.0), one per catalog entry, appended after the four numeric features. The matching domain index gets `1.0`; all others get `0.0`.

**Rationale**: Standard one-hot encoding for nominal categories. Float type (not int/bool) keeps the vector type uniform (`tuple[float, ...]`) and compatible with the existing Min–Max and distance arithmetic without any special-casing.

**Alternatives considered**:
- Single binary flag per domain as `int`: rejected — breaks type uniformity, requires cast everywhere.
- Embedding / learned representation: rejected — out of scope; project uses pure stdlib, no ML libraries.

---

## Decision 3: Min–Max scaling scope

**Decision**: Apply Min–Max scaling only to the first 4 numeric dimensions (age, monthly_income, degree_rank, daily_learning_hours). The 10 one-hot domain dimensions are passed through as-is (already in {0.0, 1.0}).

**Rationale**: Min–Max scaling on binary features is either a no-op (when both 0 and 1 appear in corpus → scaled to 0 and 1 unchanged) or undefined (when only one value appears → `hi == lo`, existing `minmax_scalar` returns 0.0, collapsing meaningful 1.0 values to 0.0). Bypassing scaling for one-hot bits avoids both the edge case and unnecessary computation.

**Alternatives considered**:
- Scale all 14 dimensions including one-hot: rejected — triggers the `hi == lo → 0.0` edge case when all profiles share a domain, destroying information.
- Store dummy ScalingStats (min=0, max=1) for domain slots: evaluated — works for the constant-dimension case since `minmax_scalar(1.0, 0.0, 1.0) = 1.0` and `minmax_scalar(0.0, 0.0, 1.0) = 0.0` but still breaks when a domain is absent from corpus (hi==lo==0 → collapses all to 0.0). Bypass is simpler and correct.

---

## Decision 4: ScalingStats structure at 14 dimensions

**Decision**: Expand `ScalingStats.mins` and `ScalingStats.maxs` from 5-float tuples to 14-float tuples. Domain slots (indices 4–13) store placeholder values (min=0.0, max=1.0) to keep the structure uniform and compatible with `from_normalized`.

**Rationale**: Keeping `ScalingStats` as a fixed-length tuple matching `VECTOR_DIM` preserves the existing structural contract that code in `jsonio.py`, `dataset.py`, and `helper.py` relies on. The placeholders are never consumed for scaling (Decision 3 bypasses them for domain slots), so their value is arbitrary — 0.0/1.0 chosen to make `minmax_scalar` a no-op if accidentally applied.

**Alternatives considered**:
- Store only 4-dim ScalingStats (numeric dims only): rejected — breaks structural uniformity; callers that zip stats with vector dims would need special indexing.
- Omit ScalingStats change and just branch in `apply_minmax`: evaluated — same effect but less transparent; keeping full 14-dim stats makes the data model self-describing.

---

## Decision 5: `QUERY_WEIGHT_KEYS` naming for domain slots

**Decision**: Add 10 new weight keys named `"domain_<catalog_name>"` (e.g. `"domain_software"`, `"domain_data_science"`, ...) matching the `DOMAIN_CATALOG` order. The full 14-key sequence is:

```
age, monthly_income, education, daily_learning_hours,
domain_software, domain_data_science, domain_finance, domain_healthcare,
domain_education, domain_manufacturing, domain_retail, domain_research,
domain_design, domain_operations
```

**Rationale**: Descriptive names tie each weight directly to a human-readable domain, making query JSON self-documenting and avoiding index-based confusion. Using a consistent prefix `"domain_"` groups the new keys visually.

**Alternatives considered**:
- Positional names `"domain_0"` … `"domain_9"`: rejected — not human-readable; reviewers cannot verify correctness without cross-referencing the catalog.
- Single `"domain"` weight applying equally to all slots: rejected — violates spec FR-001 which requires one dimension per catalog entry; also prevents users from up-weighting a specific domain.

---

## Decision 6: Refactoring `union_bbox` / `bbox_of_point` in `helper.py`

**Decision**: Replace the hard-coded 5-element tuple construction in `union_bbox` and `bbox_of_point` with loop-based construction using `tuple(...)` and generator expressions, driven by `VECTOR_DIM`.

**Rationale**: The existing code explicitly indexes `[0]` through `[4]`. Expanding to 14 explicit index references is fragile and unreadable. A loop driven by `VECTOR_DIM` ensures correctness for any future dimension change and eliminates 28 hard-coded index lines.

**Alternatives considered**:
- Manually expand to 14 index references: rejected — verbose, error-prone, fails constitution Principle II (readability and maintainability).

---

## Decision 7: Test strategy

**Decision**: Update existing `unittest`-based tests to use 14-dim vectors/stats. Add new test class `TestOneHotEncoding` in `test_pipeline.py` covering: single-domain profiles, all-catalog round-trip, one-hot mutual exclusivity, query alignment, and the corpus-with-single-domain edge case.

**Rationale**: Constitution requires stdlib-only testing (`unittest`). Existing tests that build 5-tuples will fail at runtime after the change (type errors or length-check errors), so they must be updated. New tests are scoped to the encoding contract (spec SC-001 through SC-005).

**Alternatives considered**:
- Separate new test file: acceptable but adds a file; placing tests in the existing `test_pipeline.py` keeps encoding tests co-located with normalization tests.
