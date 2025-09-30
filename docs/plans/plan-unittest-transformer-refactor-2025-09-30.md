# Plan: unittest transformer refactor

**Date:** 2025-09-30  
**Owner:** GitHub Copilot pairing with Jim Schilling  
**Related research:** `docs/research/research-unittest-transformer-refactor-2025-09-30.md`

## Goal
Refactor `splurge_unittest_to_pytest/transformers/unittest_transformer.py` to decompose oversized methods into smaller, single-purpose helpers while preserving existing behavior and test coverage.

## Scope & boundaries
- In scope: helper extraction within `UnittestToPytestCstTransformer`, introduction of supporting dataclasses/helpers, and unit test additions for new helpers.
- Out of scope: Overhauling assertion transformers, CLI integration, or unrelated modules.

## Acceptance criteria
- [ ] `leave_Module`, `leave_FunctionDef`, and `transform_code` orchestrate high-level flow, each delegating to clearly named helpers.
- [ ] Nested inheritance transformers are promoted to dedicated classes/functions with docstrings and unit coverage.
- [ ] Constructor state is organized via dedicated helper structures or dataclasses without altering public API.
- [ ] Existing unit/integration suites (`pytest tests`) pass without regressions.
- [ ] New unit tests cover extracted helpers’ decision logic (e.g., top-level node dropping, fixture collection order).

## Testing strategy
- Unit: add targeted tests under `tests/unit/` for new helpers (e.g., `test_unittest_transformer_structure.py`).
- Integration: run existing focused suites (`pytest tests/unit/test_unittest_transformer*.py`).
- Regression: run full suite `pytest` to confirm parity.
- Static analysis: `mypy splurge_unittest_to_pytest` and `ruff check` (if configured) before merge.

## Execution plan

### Stage-1: Baseline helper extraction setup
- Task-1.1: ✅ Create feature branch `refactor/unittest-transformer` from current work branch.
- Task-1.2: ✅ Introduce private helper `_should_drop_top_level_node` and `_compute_module_insert_index`, including unit tests.
- Task-1.3: ✅ Add helper `_collect_module_fixtures` returning fixtures; adjust `leave_Module` to call it.
- Task-1.4: ✅ Run targeted unit tests for module-level helper coverage.

### Stage-2: `leave_Module` decomposition
- Task-2.1: ✅ Extract `_rebuild_class_def` to handle docstrings, fixture injection, and lifecycle pruning per class.
- Task-2.2: ✅ Extract `_wrap_top_level_asserts` to isolate caplog handling.
- Task-2.3: ✅ Refactor `leave_Module` to orchestrate helpers with minimal inline logic.
- Task-2.4: ✅ Update/extend unit tests to validate class fixture insertion paths.

### Stage-3: `leave_FunctionDef` refactor
- Task-3.1: ✅ Add helper `_rewrite_function_decorators` to encapsulate skip decorator rewrites and pytest import flagging.
- Task-3.2: ✅ Add helper `_convert_simple_subtests` to handle parametrize logic and fixture injection decisions.
- Task-3.3: ✅ Add helper `_ensure_fixture_parameters` to manage `request`/`caplog` parameters consistently.
- Task-3.4: ✅ Extract `_apply_recursive_with_rewrites` for `_recursively_rewrite_withs` calls.
- Task-3.5: ✅ Refresh unit coverage for subtest parametrization and fixture insertion scenarios.

### Stage-4: `transform_code` pipeline restructuring
- Task-4.1: ✅ Extract `_parse_to_module`, `_visit_with_metadata`, `_apply_recorded_replacements` helpers.
- Task-4.2: ✅ Create `_apply_recursive_with_cleanup` to centralize `_recursively_rewrite_withs` application.
- Task-4.3: ✅ Create `_finalize_transformed_code` to wrap inheritance cleanup, import adjustments, regex fallbacks, and validation.
- Task-4.4: ✅ Add unit tests (where feasible) or integration assertions to ensure pipeline ordering remains unchanged.

### Stage-5: Inheritance cleanup reorganization
- Task-5.1: ✅ Promote nested transformer classes into separate private classes (`_RemoveUnittestTestCaseBases`, etc.) with docstrings.
- Task-5.2: ✅ Introduce `_run_inheritance_cleanup` orchestrator calling the lifted transformers.
- Task-5.3: ✅ Unit test inheritance cleanup behavior using minimal CST inputs.

### Stage-6: State encapsulation
- Task-6.1: ✅ Define dataclasses (e.g., `FixtureCollectionState`, `RegexImportTracker`) to hold constructor state.
- Task-6.2: ✅ Refactor constructor and call sites to use the encapsulated state objects.
- Task-6.3: ✅ Ensure serialization helpers (`_extract_method_body`) remain compatible with new state.

### Stage-7: Validation & polish
- Task-7.1: ✅ Run `mypy splurge_unittest_to_pytest`.
- Task-7.2: ✅ Run `pytest tests/unit/test_unittest_transformer*.py`.
- Task-7.3: ✅ Run full `pytest` suite.
- Task-7.4: ✅ Update CHANGELOG with summary of refactor (if required by repo standards).

## Risk mitigation
- Refactor incrementally, committing after each stage to isolate regressions.
- Maintain comprehensive test passes between stages to catch behavioral drift early.
- Coordinate with collaborators to avoid overlapping modifications to the transformer module during the refactor window.

## Review & sign-off
- Primary reviewer: TBD (recommend someone familiar with libcst pipeline).
- Merge criteria: all acceptance criteria satisfied, tests passing, and reviewer approval.
