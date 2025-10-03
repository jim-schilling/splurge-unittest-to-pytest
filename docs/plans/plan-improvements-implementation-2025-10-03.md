# Implementation Plan: Improvements Roadmap

Date: 2025-10-03
Author: automated review assistant (paired)

This document is a concrete implementation plan for the prioritized refactors and robustness improvements recommended in
`docs/research/research-opportunities-for-improvements-2025-10-03.md`.

Goals
- Reduce module complexity and duplication.
- Improve observability of transformation failures during development and CI.
- Separate pure validation from side-effects for IO helpers.
- Harden parametrize conversion heuristics and make them easier to test.

How to read this file
- Priorities are grouped into High, Medium-High, Medium, Low.
- Each priority is split into Stages and Tasks.
- Each Task contains: Scope, Specifications / Contracts, Acceptance Criteria, Implementation Notes, and Tests.


## High Priority

Rationale: Low-risk, high-value changes that reduce duplication and improve debugability. These are quick wins with strong ROI.

### Stage 1: Extract caplog helpers (very low risk)

Task 1.1 - Create `transformers/_caplog_helpers.py`
- Scope: Add a small helper module exposing functions to detect and rewrite caplog-related AST patterns and to build caplog expression fragments used by multiple transformers.
- Files to create/update:
  - `splurge_unittest_to_pytest/transformers/_caplog_helpers.py` (new)
  - `splurge_unittest_to_pytest/transformers/assert_transformer.py` (update imports + replace duplicated code)
- Contract:
  - Inputs: a `libcst.CSTNode` representing an expression or statement.
  - Outputs: typed libcst nodes or dataclasses describing the alias access (example dataclass `AliasOutputAccess(alias: str, slice: Optional[cst.BaseExpression])`).
  - Error behavior: return `None` if the shape is not recognized; do not raise for unexpected inputs.
- Acceptance criteria:
  - All existing behaviour for caplog handling remains unchanged as validated by unit tests and full test-suite.
  - No duplication remains in `assert_transformer.py` for caplog alias detection; tests for the moved helpers exist.
- Implementation notes:
  - Keep API minimal: `extract_alias_output_slices(node) -> AliasOutputAccess | None`, `build_caplog_records_expr(access) -> cst.BaseExpression`, `build_get_message_call(access) -> cst.Call`.
- Tests:
  - Unit tests for 6 representative AST patterns (plain attribute, subscripted, alias with asname, nested attribute) asserting expected returned structure and generated code.

Task 1.2 - Update `assert_transformer.py` to use helpers
- Scope: Replace duplicated code sections that detect alias.output slices and build caplog AST with calls to `_caplog_helpers`.
- Acceptance criteria:
  - Code compiles and tests pass.
  - Diff is small and reviewers can easily see logic moved vs changed.


### Stage 2: Add TRANSFORM_DEBUG and improve error surfacing (low risk)

Task 2.1 - Add a small debug gate
- Scope: Add a module-level helper `transformers/debug.py` or a small utility function in `transformer_helper.py` that reads `SPLURGE_TRANSFORM_DEBUG` env var.
- Contract:
  - `get_transform_debug() -> bool` reads `os.getenv("SPLURGE_TRANSFORM_DEBUG", "") in {"1","true","True"}`.
  - A helper `maybe_reraise(exc: Exception)` will re-raise when debug is enabled; otherwise will optionally log.
- Acceptance criteria:
  - When `SPLURGE_TRANSFORM_DEBUG=1` and a transform helper encounters an unexpected exception, the exception is re-raised (tests should demonstrate this using a small injected failure).
  - Default behaviour remains silent/conservative to preserve existing safety in non-debug mode.
- Implementation notes:
  - Place usage points in: `record_replacement`, `_apply_recorded_replacements`, and top-level transform invocation `transform_code` where we catch broad exceptions.
- Tests:
  - Unit test that sets env var and asserts that a deliberately broken helper raises; counterpart test asserts no raise in default mode.


## Medium-High Priority

Rationale: Slightly more invasive but still contained refactors that improve testability and reduce surprise side-effects.

### Stage 1: Make `helpers/path_utils.validate_target_path` pure (low risk)

Task 3.1 - Separate validation from side-effects
- Scope:
  - Update `helpers/path_utils.py` to split `validate_target_path` into two functions:
    - `validate_target_path(path: str | Path, allow_long_paths: bool = False) -> Path` (pure validation)
    - `ensure_parent_dir(path: str | Path, exist_ok: bool = True) -> None` (side-effects)
- Specifications / Contracts:
  - `validate_target_path` must not create directories or modify FS.
  - It returns a `Path` instance or raises `ValueError`/`PermissionError` on invalid conditions.
  - Writability check should be implemented via a small attempt to create a temporary file in the parent directory (os.open with O_CREAT|O_EXCL) and immediately remove it — this is more reliable than `os.access` on Windows.
  - `ensure_parent_dir` performs `Path(path).parent.mkdir(parents=True, exist_ok=exist_ok)` and raises on failure.
- Acceptance criteria:
  - All call sites are updated to call `ensure_parent_dir` where they previously relied on `validate_target_path` side-effects.
  - Tests cover both functions using `tmp_path` fixtures and assert behavior on unwritable directories (using pytest's `monkeypatch` to simulate PermissionError where necessary).
- Backwards compatibility notes:
  - If any public API expected `validate_target_path` to create parents, update its callers in the CLI and script entrypoints.
- Tests:
  - Unit tests for `validate_target_path` returning valid `Path` for normal inputs, raising on invalid. Integration test that calls `ensure_parent_dir` and writes a file.


## Medium Priority

Rationale: Useful structural refactors that require more careful testing and staged rollout.

### Stage 1: Extract parametrize name-resolution (medium risk)

Task 4.1 - Move `_resolve_name_reference` and related helpers to `transformers/_resolvers.py`
- Scope:
  - Create a new module `transformers/_resolvers.py` containing `resolve_name_reference(name, statements, loop_index) -> (values, removable_index | None) | None`, mutation detection helpers, `_collect_constant_assignment_values`, and `_inline_constant_expression`.
- Contract:
  - Functions must be pure: accept `statements` (Sequence[cst.BaseStatement]) and `loop_index` and return deterministic results.
  - Mutation detection returns True/False and provides clear documentation of the mutation heuristics (append/extend/assign/augassign and expression assignments).
- Acceptance criteria:
  - `parametrize_helper` should import the resolvers and call them with identical semantic behavior; tests should demonstrate parity on a representative fixture suite.
- Implementation notes:
  - Add property-based tests (pytest + hypothesis optional) to generate small statement sequences and assert invariants.
- Tests:
  - Unit tests that mirror previous `_resolve_name_reference` behavior, including: appended mutations, augmented assignments, multi-statement initializers, and non-resolvable cases.

Task 4.2 - Make convert function explicitly accept options
- Scope: Introduce a dataclass `ParametrizeOptions(parametrize_include_ids: bool, parametrize_add_annotations: bool)` and change `convert_subtest_loop_to_parametrize` signature to accept it rather than reading transformer attributes.
- Acceptance criteria:
  - Tests for parametrize behavior should construct `ParametrizeOptions` explicitly and validate decorated output remains unchanged.


## Low Priority

Rationale: Larger changes or nice-to-have features that are lower immediate ROI but improve long-term maintainability.

### Stage 1: Incrementally split `assert_transformer.py` (medium risk)

Task 5.1 - Identify logical boundaries and extract modules
- Scope:
  - Create `assert_ast_rewrites.py` (small pure functions operating on libcst nodes), `assert_with_rewrites.py` (helpers to transform With/Try bodies), and `assert_fallbacks.py` (string/regex-based fallbacks isolated and behind a flag).
- Contract:
  - Public APIs are pure functions with well-defined inputs and outputs.
- Acceptance criteria:
  - No change to observable behavior with default settings; isolated fallback module behind an `aggressive_fallbacks` flag in config.
- Tests:
  - Unit tests for each extracted module using representative cases.

Task 5.2 - Add fallback corpus
- Scope:
  - Add `tests/fixtures/fallback_cases/` with pairs of input/output cases exercised by unit tests for `assert_fallbacks`.
- Acceptance criteria:
  - Tests fail if fallback changes output unexpectedly.


## Cross-cutting concerns

1. Testing strategy
- For each functional extraction, add unit tests (happy path + 2–3 edge cases). Integration tests run the whole transform pipeline on small real-world-like files to confirm end-to-end parity.
- Use `tmp_path` for filesystem tests; use `monkeypatch` to simulate permission errors or platform-specific behavior.

2. CI / tooling
- Add a CI job (or extend existing) that runs the test-suite with `SPLURGE_TRANSFORM_DEBUG=1` once for the PR pipeline to surface transformation exceptions early.
- Add `ruff` and `mypy` jobs progressively; start with `--ignore-missing-imports` then tighten.

3. Developer ergonomics
- Add a short `docs/development/README.md` describing how to enable debug, run targeted tests, and add new fallback fixtures.


## Acceptance criteria for the overall program
- All unit tests pass locally and in CI after each staged PR.
- Each extracted helper has unit tests with at least 80% coverage of its public API.
- No behavioral regressions on the repository's transformation tests (run representative end-to-end transformations used by the current test-suite).
- PRs are small, focused (< 300 lines change) where possible, and include changelog entries.


## Rollout plan
- Execute the High priority items as individual PRs, run full test-suite for each PR.
- Merge Medium-High priority items once high priority PRs are green and stable.
- For Medium priority extractions, produce stage gates and small PRs with follow-up tests.
- Defer Low priority broader refactors to a dedicated branch and break into small PRs.


---

Notes
- If you want, I can start implementing the first PR (`transformers/_caplog_helpers.py`) now and add unit tests, open a branch, and run the test-suite.

Finalization notes (Stage 1 & 2)

- Refactor summary: caplog-related detection and AST-construction logic was extracted from `assert_transformer.py` into `splurge_unittest_to_pytest.transformers._caplog_helpers`. This centralizes duplicate logic for alias output/records detection and for constructing `caplog.records[...]` and `.getMessage()` calls.
- Compatibility shims: small wrapper functions and an exported dataclass were re-exported from `assert_transformer.py` to preserve the original module's public API (tests and other modules import underscore-prefixed helpers from `assert_transformer`). These shims are intentionally thin and delegate to the extracted helpers to keep reviewers' diffs small and preserve backwards compatibility.
- Debug gate: a tiny `transformers/debug.py` helper (`get_transform_debug()` and `maybe_reraise()`) was added. When `SPLURGE_TRANSFORM_DEBUG` is truthy the code will re-raise transformation exceptions to aid debugging; by default behaviour is conservative and non-raising.
- Tests added: unit tests were added for the new helpers and for the debug gate (`tests/unit/test_caplog_helpers_basic.py`, `tests/unit/test_debug_gate_basic.py`). The full test-suite was run and is green. These tests serve as the acceptance criteria for the refactor.

Next steps: open a small PR with this change-set, include the new tests, and add a CI job to run the suite once with `SPLURGE_TRANSFORM_DEBUG=1` to surface exceptions during review.

