# Plan: Codebase Simplification — 2025-09-12

This document captures a small, safe, prioritized plan to simplify the
`splurge-unittest-to-pytest` codebase. It is intentionally conservative: the
plan focuses on small, testable, and reversible changes to reduce duplication
and cognitive overhead without changing behavior.

Historical note
---------------
The compatibility-mode and engine selection options (for example, `--no-compat` and `engine=`) were removed in release 2025.1.0. This plan is retained for historical context.

Owners: Jim Schilling (maintainer)
Status: Draft

## Goals

- Reduce duplicated normalization/parsing logic and centralize small helpers.
- Improve readability by extracting multi-step checks into named helpers.
- Preserve existing public API and behavior; prefer non-breaking internal moves.
- Provide a small pilot refactor to validate the approach.

## Priorities and stages (checklist)

 - [x] Stage 0  Preparation
  - [x] Create `tests/unit` tests for parsing and normalization helpers (if missing)
  - [ ] Add CI job to run unit tests and linters locally (existing CI likely covers this)

 - [x] Stage 1  Quick wins (low-risk)
  - [x] Add `converter/utils.has_meaningful_changes(original, converted)` helper
  - [x] Move CLI `_parse_method_patterns` into `converter/utils.parse_method_patterns`
  - [x] Replace inline calls in `main.py`/`cli.py` to use these helpers
  - [x] Add unit tests for `has_meaningful_changes` and `parse_method_patterns`
  - [x] Run ruff/mypy/pytest and fix issues

 - [x] Stage 2 — Consolidate normalization (low-to-medium risk)
  - [x] Ensure `normalize_method_name` is the single normalization function used
  - [x] Update `PatternConfigurator` and any other callers to use `normalize_method_name`
  - [x] Add unit tests for `normalize_method_name` edge cases (camelCase, underscores, digits)

 - [x] Stage 3 — Reduce micro-modules (medium risk)
  - [x] Consolidate closely-related helpers into `converter/helpers.py` and remove compatibility shim
  - [x] Update internal imports to use `converter.helpers` (no backwards-compatibility shim retained)
  - [x] Run full test suite and linters

- [ ] Stage 4 — Assertion helpers tidy (medium risk)
 - [x] Stage 4 — Assertion helpers tidy (medium risk)
  - [x] Consider grouping similar functions in `converter/assertions.py` into a map
  - [x] Add tests for assertion conversion helpers
  - [x] Ensure consumer stages call the mapping instead of individual functions
  - Note: Added `ASSERTIONS_MAP` to `converter/assertions.py` and updated
    `converter/assertion_dispatch.py` to use it. This centralizes the mapping
    of unittest assertion names to converter functions and simplifies dispatch.

- [ ] Stage 5 — Pipeline & diagnostics (opt-in)
  - [ ] Move diagnostic writes out of `stages/pipeline.py` into a diagnostics helper or StageManager hook
  - [ ] Make diagnostics opt-in via `SPLURGE_ENABLE_DIAGNOSTICS` (leave behavior unchanged until enabled)

- [ ] Stage 6 — API surface & cleanup (deferred)
  - [ ] Review `__init__.py` exports and document the stable public API
  - [ ] Optionally trim or clearly document deprecated exports

## Tasks (detailed)

1. Create `converter/helpers.py` helpers
   - Implement `has_meaningful_changes(original, converted) -> bool` which:
     - Normalizes both modules (using existing `formatting.normalize_module`), compare normalized code
     - Fall back to AST compare via `ast.parse`/`ast.dump` if normalization fails
     - Fall back to direct string compare
   - Implement `parse_method_patterns(pattern_args: tuple[str,...]) -> list[str]` that mirrors CLI behavior

2. Update call-sites
   - Replace block in `main.convert_string` that performs normalization/AST checks with a call to `has_meaningful_changes`
   - Replace `_parse_method_patterns` in `cli.py` with `parse_method_patterns`

3. Add tests
   - Add unit tests under `tests/unit` for:
     - `parse_method_patterns`: multiple flags, comma-separated strings, whitespace trimming, duplicates
     - `has_meaningful_changes`: formatting-only changes, AST-equivalent changes, real changes
     - `normalize_method_name` edge cases

4. Run quality gates
   - Run `ruff check .` and `mypy` and `pytest` locally. Fix minor typing/lint issues caused by refactor.

5. Iterate & merge
   - Create a small PR for Stage 1 changes only. Keep changes small and focused.
   - Once Stage 1 is green, proceed to Stage 2 and repeat.

## Acceptance criteria

- All unit tests pass and CI is green.
- No change in conversion behavior observed in end-to-end tests.
- Codebase is easier to navigate (fewer duplicated normalization/parsing functions).

## Rollback plan

- Keep `converter/core.py` or other original modules as compatibility shims during migration.
- If a step causes regressions, revert the PR and open an issue with the failing test/logs.

## Notes

- Avoid renaming public import paths in a single commit. Prefer internal moves behind compatibility shims.
- Add documenting comments to any moved helpers explaining why they were moved.

---

Generated: 2025-09-12
