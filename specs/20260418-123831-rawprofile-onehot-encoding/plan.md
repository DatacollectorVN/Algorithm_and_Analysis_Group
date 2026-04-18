# Implementation Plan: One-Hot Encoding for favourite_domain in RawProfile Normalization

**Branch**: `20260418-123831-rawprofile-onehot-encoding` | **Date**: 2026-04-18 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/20260418-123831-rawprofile-onehot-encoding/spec.md`

## Summary

Replace label encoding of `favourite_domain` (a nominal categorical field) with one-hot encoding during `RawProfile` normalization. `highest_degree` retains its existing ordinal encoding. This expands the normalized vector from 5 to 14 dimensions (4 numeric + 10 one-hot domain bits). All downstream structures (`ProfileVector`, `ScalingStats`, distance functions, weight keys, helper geometry) are updated accordingly — using only the Python Standard Library.

## Technical Context

**Language/Version**: Python 3.12 (uses `type` alias syntax)  
**Primary Dependencies**: Standard Library only (`dataclasses`, `json`, `math`, `random`, `pathlib`, `unittest`) — **no PyPI packages**  
**Storage**: JSON files (corpus and query on disk)  
**Testing**: `unittest` (stdlib)  
**Target Platform**: CPython, any OS  
**Project Type**: CLI / library  
**Performance Goals**: Linear O(n) in corpus size for normalization  
**Constraints**: Standard Library only (hard gate — constitution Principle I)  
**Scale/Scope**: Corpus sizes up to ~10,000 profiles per spec SC-003

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Standard Library First | PASS | No new dependencies; one-hot encoding is pure arithmetic |
| II. Style, Typing, Functional-First | PASS | `ProfileVector → tuple[float, ...]`; pure functions; PEP 8 |
| III. O(n) Memory & Algorithmic Efficiency | PASS | One-hot encoding is O(1) per profile; normalization remains O(n) |
| IV. Google-style Docstrings | PASS | All modified public functions require docstring updates |
| V. Domain Errors via Exception Hierarchies | PASS | `ValidationError` (existing hierarchy) raised on bad `favourite_domain` |
| Testing: stdlib unittest only | PASS | All tests use `unittest`; no pytest |
| Hard gate: no PyPI | PASS | Confirmed — zero new imports beyond stdlib |

**Post-design re-check**: All gates still pass. No complexity tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/20260418-123831-rawprofile-onehot-encoding/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (files modified by this feature)

```text
src/
└── services/
    ├── constants.py              # VECTOR_DIM 5→14; QUERY_WEIGHT_KEYS 5→14 keys
    ├── dto/
    │   ├── __init__.py           # Docstring update only
    │   └── profiles.py           # ProfileVector, ScalingStats, NormalizedProfile
    ├── dataset.py                # domain_to_index→domain_to_onehot; raw_to_prevector;
    │                             # apply_minmax; compute_scaling_stats
    ├── helper.py                 # union_bbox, bbox_of_point → loop-based
    ├── jsonio.py                 # load_query_json weights tuple (5→14)
    └── search/
        └── distance.py           # Type hints; error message length reference

tests/
├── test_pipeline.py              # Update 5-dim fixtures; add TestOneHotEncoding
├── test_distance.py              # Update 5-dim fixtures to 14-dim
├── test_baseline.py              # Update weight/vector fixtures
├── test_kdtree.py                # Update weight/vector fixtures
├── test_jsonio.py                # Update query JSON weight keys
└── test_scale_smoke.py           # Update expected vector lengths
```

**Structure Decision**: Single-project layout (existing). No new files or directories created in `src/`.

## Complexity Tracking

> No constitution violations. Section left intentionally empty.
