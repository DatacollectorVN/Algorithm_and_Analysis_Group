<!--
Sync Impact Report
- Version change: (template placeholders) → 1.0.0
- Principles established (replacing template slots):
  - PRINCIPLE_1 → I. Standard Library First
  - PRINCIPLE_2 → II. Style, Typing, and Functional-First Modularity
  - PRINCIPLE_3 → III. Memory and Algorithmic Efficiency
  - PRINCIPLE_4 → IV. Documentation (Google Style)
  - PRINCIPLE_5 → V. Domain Errors via Exception Hierarchies
- Added sections: Testing & Verification; Development Workflow & Quality Gates
- Removed sections: none (template placeholders replaced with concrete sections)
- Templates: .specify/templates/plan-template.md ✅ | spec-template.md ✅ |
  tasks-template.md ✅ | checklist-template.md (unchanged; no constitution refs) |
  agent-file-template.md ✅ | .specify/templates/commands/*.md ⚠ not present in repo
- Follow-up TODOs: none
-->

# RMIT Algorithm Analysis — Group Project Constitution

## Core Principles

### I. Standard Library First

- The codebase MUST NOT declare or rely on third-party packages from PyPI or other
  external package indexes. No `pip install` dependencies for runtime, tests, or
  tooling shipped as part of this repository.
- All behavior MUST be implemented using the Python Standard Library only (for
  example: `json`, `datetime`, `collections`, `dataclasses`, `logging`,
  `unittest`, `asyncio`, `pathlib`, `typing`, `itertools`, `functools`).
- **Rationale**: Minimizes supply-chain and environment drift, keeps the project
  portable and reproducible on a plain Python install, and aligns with course
  algorithm-analysis goals (clear, inspectable code paths).

### II. Style, Typing, and Functional-First Modularity

- Code MUST comply with [PEP 8](https://peps.python.org/pep-0008/).
- Public APIs and non-trivial internal functions MUST use strict, modern type
  hints (`list[str]`, `dict[str, Any]` only where unavoidable, prefer concrete
  types). Avoid untyped public surfaces except where PEP explicitly allows
  omission.
- Design MUST favor small, composable **pure functions** and explicit data flow;
  modules SHOULD expose clear boundaries (package layout, minimal mutable shared
  state). Use classes where they model state or protocols clearly; avoid
  unnecessary OO layering.
- **Rationale**: Readability for review and assessment, early defect detection via
  types, and simpler reasoning about complexity.

### III. Memory and Algorithmic Efficiency

- Data structures and core algorithms MUST be chosen so that typical batch
  operations on primary inputs are **O(n)** or better in time and proportional in
  extra space unless a violation is documented with justification (for example,
  unavoidable problem lower bounds or explicit spec requirement).
- Implementations MUST favor memory-efficient representations (avoid redundant
  copies, prefer generators/iterators where appropriate, use `__slots__` or
  compact layouts only when measured or clearly warranted).
- **Rationale**: The project centers on algorithm analysis; complexity and memory
  behavior must be intentional, not accidental.

### IV. Documentation (Google Style)

- Every public module, class, and function MUST have **Google-style** docstrings:
  summary line, `Args`, `Returns`, `Raises` where applicable, and optional
  `Examples` for non-obvious usage.
- **Rationale**: Consistent, scannable documentation for peers and assessors.

### V. Domain Errors via Exception Hierarchies

- The project MUST define **custom exception** class hierarchies rooted at a
  small set of domain base exceptions (for example, `ProjectError`). Standard
  library exceptions MAY propagate for truly unexpected interpreter/OS failures,
  but **business and contract violations** MUST map to project-defined types.
- Error messages MUST be actionable; avoid bare `except:` and avoid swallowing
  exceptions without logging or re-raising with context where appropriate
  (`logging` stdlib).
- **Rationale**: Predictable failure modes for tests and callers, clearer
  separation of domain vs. environmental errors.

## Testing & Verification

- Automated tests MUST use the **Standard Library only** (`unittest` and, where
  needed, `asyncio` test patterns compatible with `unittest`). No pytest or
  other third-party test frameworks.
- Tests MUST exercise public contracts and critical edge cases; new behavior MUST
  not merge without tests that would fail if the behavior were wrong (unless
  the feature spec explicitly defers testing, which must be recorded in the spec).
- **Rationale**: Keeps the dependency rule intact while preserving verifiability.

## Development Workflow & Quality Gates

- Every change MUST be reviewed against this constitution: imports restricted to
  the standard library, PEP 8 and type hints present, Google docstrings on public
  API, and domain errors routed through the project exception hierarchy.
- Complexity or memory trade-offs that deviate from Principle III MUST be called
  out in the implementation plan (`Complexity Tracking` in `plan.md`) or in the
  feature spec.
- Feature plans and tasks MUST treat “no PyPI dependencies” as a **hard gate**,
  not a default suggestion.

## Governance

- This constitution supersedes conflicting ad-hoc practices for this repository.
- **Amendments**: Propose a PR that updates `.specify/memory/constitution.md`,
  bumps the version line below per semantic versioning, sets **Last Amended** to
  the merge date, and updates dependent templates when principles change.
- **Versioning (this document)**:
  - **MAJOR**: Removal or incompatible redefinition of a principle or gate.
  - **MINOR**: New principle, section, or materially expanded obligation.
  - **PATCH**: Clarifications, wording, typos, non-semantic refinements.
- **Compliance**: Maintainers and reviewers MUST block merges that violate Core
  Principles unless the feature’s `plan.md` documents an approved exception path
  (rare; does not waive Standard Library First without explicit governance
  amendment).

**Version**: 1.0.0 | **Ratified**: 2026-04-04 | **Last Amended**: 2026-04-04
