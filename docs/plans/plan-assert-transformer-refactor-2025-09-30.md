# Plan: assert transformer refactor

**Date:** 2025-09-30  
**Owner:** GitHub Copilot pairing with Jim Schilling  
**Related research:** TBD (`docs/research/research-assert-transformer-refactor-2025-09-30.md`)

## Goal
Refactor `splurge_unittest_to_pytest/transformers/assert_transformer.py` so that large, multi-purpose routines (especially `rewrite_single_alias_assert`) are decomposed into cohesive helpers with single responsibilities while preserving existing transformation behavior and public APIs.

## Scope & boundaries
- In scope: restructuring assertion rewriting helpers, extracting pure functions/data classes, and enhancing unit coverage around rewritten helpers.
- Out of scope: modifying CLI interfaces, unrelated transformers, or changing user-facing configuration semantics.

## Acceptance criteria
- [ ] `rewrite_single_alias_assert` delegates to named helpers (e.g., extraction, comparison rewrites, boolean rewrites) with each helper limited to one logical concern and documented.
- [ ] No helper newly introduced exceeds 50 logical lines or embeds nested responsibilities (per code review checklist).
- [ ] New helpers are covered by focused unit tests capturing alias/output permutations, unary/membership paths, and failure fallbacks.
- [ ] Existing pytest suites (`pytest tests`) pass without behavioral regressions and coverage for `assert_transformer.py` remains ≥ prior baseline.
- [ ] Updated developer documentation (README-DETAILS or transformer docstrings) reflects the new helper structure.

## Testing strategy
- Unit: add or expand tests in `tests/unit/test_assert_transformer_*` to validate each new helper and edge cases (e.g., unary negation, membership, chained subscripts).
- Integration: run focused suites touching assertion conversions (`pytest tests/unit/test_assert_transformer*.py tests/integration/test_comprehensive_assertions.py`).
- Regression: execute full `pytest` run post-refactor to confirm no downstream regressions.
- Static analysis: `ruff check` and `mypy splurge_unittest_to_pytest` before merge.

## Execution plan

### Stage-1: Baseline analysis & guardrails
- [x] Task-1.1: Capture current complexity metrics (lines, branches) for `rewrite_single_alias_assert` and related helpers using `python -m radon cc` or similar.
	- Command: `python -m radon cc -s -a splurge_unittest_to_pytest/transformers/assert_transformer.py`
	- Highlights: `rewrite_single_alias_assert` scores **F (106)**; other hotspots `wrap_assert_in_block` **D (30)** and `_recursively_rewrite_withs` **D (24)**. Average module complexity currently **B (7.11)**.
- [x] Task-1.2: Map existing helper flow (e.g., `_rewrite_comparison_expr`, `_try_unary_comparison_rewrite`) into a diagram/checklist to identify natural seams.
	- `rewrite_single_alias_assert` declares nested helpers responsible for (a) alias/slice extraction (`_extract_attr_and_slices`), (b) caplog record construction (`_build_caplog_subscript`), (c) comparison rewrites (length/membership/equality via `_rewrite_comparison_expr`), (d) recursive expression traversal (`rewrite_expr` handling Boolean/Parenthesized/Unary nodes), and (e) unary-specific membership rewrites (`_try_unary_comparison_rewrite`).
	- External collaborators include `rewrite_following_statements_for_alias` (subsequent call sites) and builder helpers (`build_with_item_from_assert_call`, `transform_with_items`) that supply alias contexts.
	- Pain points: duplication between inline `_eq_inline` logic and `_rewrite_eq_node`, repeated alias/output guards, and interdependent nested helpers limiting reuse.
- [x] Task-1.3: Snapshot current unit/integration test results and coverage to compare after refactor.
	- Command: `pytest tests/unit/test_assert_transformer*.py tests/integration/test_comprehensive_assertions.py`
	- Result: **124 passed** in 7.07s with coverage for `assert_transformer.py` at **55%** (baseline for post-refactor comparison). Coverage artifacts updated at `coverage.xml` / `htmlcov/`.

### Stage-2: Extract alias pattern analysis helpers
- [x] Task-2.1: Create dedicated helper for alias/slice extraction (e.g., `_extract_alias_output_slices`) reused across rewrites.
  - Added `_extract_alias_output_slices`, replacing all inline alias guards inside `rewrite_single_alias_assert`.
- [x] Task-2.2: Introduce builder helpers (`_build_caplog_records_expr`, `_build_get_message_call`) with docstrings and unit tests.
  - Implemented both helpers and exercised them via `tests/unit/test_assert_transformer_alias_helpers.py`.
- [x] Task-2.3: Provide a small data structure (namedtuple/dataclass) encapsulating rewrite candidates to simplify branching logic.
  - Defined frozen dataclass `AliasOutputAccess` capturing alias and slice chain for reuse across condition paths.

### Stage-3: Recompose comparison & boolean rewrites
- [x] Task-3.1: Split comparison rewrites into specialized helpers (`_rewrite_length_comparison`, `_rewrite_membership_comparison`, `_rewrite_equality_comparison`).
	- Introduced dedicated helpers and wired them through `_rewrite_comparison`, replacing all inline alias checks.
- [x] Task-3.2: Encapsulate unary/parenthesized expression handling into `_rewrite_unary_operation` while reusing comparison helpers.
	- Added `_rewrite_unary_operation` plus recursion-aware logic so unary, boolean, and parenthesized cases share the same pipeline.
- [x] Task-3.3: Implement a dispatcher helper orchestrating rewrite attempts and returning early on first success; keep `rewrite_single_alias_assert` as a thin coordinator.
	- Added `_rewrite_expression` dispatcher and simplified `rewrite_single_alias_assert` to a few helper calls.

### Stage-4: Expand test coverage & fixtures
- [x] Task-4.1: Add unit tests for new helpers covering positive, negative, and exception paths (using fixtures in `tests/unit/test_assert_transformer_ranges_specific.py` or new module).
	- Added `pytest`-parametrized cases and negative-path assertions in `tests/unit/test_assert_transformer_expression_rewrites.py` alongside existing alias helper coverage.
- [x] Task-4.2: Add parametrized cases for nested subscripts, chained boolean operations, and `not`-prefixed patterns.
	- Nested slice and chained boolean scenarios now validate caplog rewrites while `not`-wrapped membership retains coverage via new tests.
- [x] Task-4.3: Validate behavior when rewrites should not occur (ensuring helpers return `None` gracefully) to preserve conservative defaults.
	- Added explicit assertions that mismatched aliases and unsupported unary operations return `None`.

### Stage-5: Integration & documentation
- [x] Task-5.1: Wire new helpers into `rewrite_single_alias_assert` and any other oversized methods, ensuring consistent naming and flow.
	- `rewrite_single_alias_assert` now delegates entirely to `_rewrite_expression` / `_rewrite_comparison`, while unary and boolean rewrites leverage the shared dispatcher.
- [x] Task-5.2: Run `ruff`, `mypy`, targeted pytest suites, and full suite; compare coverage with baseline snapshot.
	- Commands executed:
		- `python -m ruff check`
		- `python -m mypy splurge_unittest_to_pytest`
		- `pytest tests/unit/test_assert_transformer_alias_helpers.py tests/unit/test_assert_transformer_expression_rewrites.py`
		- `pytest`
- [x] Task-5.3: Update developer docs (docstrings, `README-DETAILS.md` if needed) summarizing helper responsibilities and migration notes.
	- `docs/README-DETAILS.md` now documents the helper pipeline and targeted tests; module docstrings refreshed earlier in Stage-3.3 follow-up.
- [x] Task-5.4: Prepare PR checklist, including acceptance criteria confirmations and reviewer guidance on new helper organization.
	- Added checklist below capturing acceptance criteria, test/lint status, and reviewer focus points.

### PR checklist
- [x] Delegation helpers documented and unit-tested (`_rewrite_expression`, `_rewrite_unary_operation`, `parenthesized_expression`).
- [x] Lint (`python -m ruff check`) and type checks (`python -m mypy splurge_unittest_to_pytest`) clean.
- [x] Tests: targeted helper suites and full `pytest` run green (492 passed, 1 skipped).
- [x] Reviewer guidance: focus on new negative-path tests in `tests/unit/test_assert_transformer_expression_rewrites.py` and parentheses metadata handling within `_rewrite_unary_operation`.

## Risk mitigation
- Decompose incrementally with git commits per helper extraction to simplify rollbacks.
- Ensure helpers remain pure (no hidden state) to ease testing and reuse.
- Guard against accidental broad rewrites by keeping conservative fallbacks and comprehensive negative tests.

## Review & sign-off
- Primary reviewer: TBD (recommend engineer familiar with assertion transformer behavior).
- Merge checklist: all acceptance criteria checked, tests and static analysis green, documentation updated, reviewer approval obtained.
