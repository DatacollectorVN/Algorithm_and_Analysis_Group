# Research: Corpus pipeline public API

## R1 — Public method naming

**Decision**: Drop the leading underscore on existing `Corpuses` static/class helpers; rename `_build_normalized_pair` to `build_normalized_corpus` so the class carries the same conceptual name as the removed module function.

**Rationale**: Matches Python convention for public API (`_` = private). One clear name (`build_normalized_corpus`) avoids a second public name (`build_normalized_pair`) that would force churn in tests and mental mapping.

**Alternatives considered**:

- Keep `build_normalized_pair` as the public name — rejected: diverges from historical module API and is less descriptive for course readers.
- Add new public names while keeping `_` duplicates — rejected: duplicates and confusion.

## R2 — Module-level aliases after removal

**Decision**: Remove all thin wrappers in `dataset.py`; callers import and call `Corpuses` methods directly. Remove `build_normalized_corpus` from `services.__all__` unless we explicitly want a second export path (we do not).

**Rationale**: User-requested cleanup; single source of truth on the class.

**Alternatives considered**:

- Keep re-export in `services/__init__.py` as `build_normalized_corpus = Corpuses.build_normalized_corpus` — rejected: still two ways to call the same thing; user asked to remove module-level functions.

## R3 — `get_synthetic_*` / `load_corpus_from_path`

**Decision**: Remove these module functions; no in-repo references found outside `dataset.py`. Any external “002 contract” callers must use `Corpuses.from_json_path` and `Corpuses.load_query` (document in quickstart/contracts if needed).

**Rationale**: Dead code in this repository; consolidation on `Corpuses` methods.

**Alternatives considered**:

- Keep for backward compatibility — rejected: user explicitly scoped removal; grep shows no internal usage.
