# Research: unittest transformer refactor

**Date:** 2025-09-30  
**Author:** GitHub Copilot (pairing with Jim Schilling)  
**Context:** `splurge_unittest_to_pytest/transformers/unittest_transformer.py`

## Objective
Document the current complexity hotspots within `UnittestToPytestCstTransformer` and outline viable decomposition strategies that retain behavior while improving maintainability.

## Current observations
- The module centralizes lifecycle handling, assertion rewrites, fixture synthesis, and final string fallbacks in a single transformer class.
- Three methods drive the bulk of the control flow and exceed reasonable cognitive load:
  - `leave_Module` orchestrates top-level cleanup, per-class fixture wiring, and module fixture insertion.
  - `leave_FunctionDef` blends decorator rewrites, parametrization conversions, fixture injection, and recursive post-processing.
  - `transform_code` couples CST traversal orchestration with string-level fallbacks, import rewrites, and validation.
- `_transform_unittest_inheritance` embeds three nested transformer classes inline, making the inheritance cleanup pipeline harder to understand and to test independently.
- The constructor initializes ~25 mutable attributes covering unrelated concerns (fixture harvesting, regex import tracking, debug state), which complicates reasoning about invariants.

## Pain points & risks
- **Testing friction:** Large, multi-purpose methods are difficult to exercise in isolation; regression coverage tends to be broad integration tests instead of targeted unit coverage.
- **Change amplification:** Touching any helper call or early return in the large methods risks unintended side effects because responsibilities are intertwined.
- **Debug complexity:** Debug trace output (currently `self.debug_trace = True`) suggests a need to step through logic manually; finer-grained helpers would reduce reliance on tracing.
- **Code review overhead:** Inline nested helper classes and multi-screen methods increase review time and hinder selective refactoring.

## Decomposition opportunities
### `leave_Module`
Break into narrowly focused helpers:
1. `_compute_module_insert_index(body)`
2. `_should_drop_top_level_node(node)`
3. `_rebuild_class_def(node)`
4. `_collect_module_fixtures()`
5. `_wrap_top_level_asserts(nodes)`

### `leave_FunctionDef`
Separate sequential steps:
1. `_rewrite_function_decorators(original, updated)`
2. `_convert_subtests_to_parametrize(original, updated)`
3. `_rewrite_subtest_body(body_stmts)`
4. `_ensure_required_fixtures(fn)`
5. `_apply_recursive_with_rewrites(fn)`

### `transform_code`
Model as a pipeline:
1. `_parse_to_module(code)`
2. `_visit_with_metadata(module)`
3. `_apply_recorded_replacements(module)`
4. `_apply_recursive_with_cleanup(module)`
5. `_finalize_output(code)` (inheritance removal, import rewrites, regex fallback, validation)

### `_transform_unittest_inheritance`
- Promote each nested transformer (removal, normalization, method renaming) into dedicated private classes with docstrings.
- Provide a high-level helper (`_run_inheritance_cleanup`) that chains them, making it easy to test and reuse.

### Constructor state
- Evaluate splitting lifecycle capture into a dedicated data structure (`FixtureCollectionState`) and regex-tracking into another (`RegexImportTracker`).
- Encapsulate stack management and fixture needs to reduce direct attribute access throughout the class.

## Recommended sequencing
1. Extract pure helper functions that require no new state (`_should_drop_top_level_node`, `_compute_module_insert_index`).
2. Introduce state-holder dataclasses for lifecycle snippets and regex metadata; transition existing attributes to use them.
3. Factor `leave_Module` into an orchestration method that delegates to newly extracted helpers.
4. Repeat the extraction pattern for `leave_FunctionDef` and `transform_code`.
5. Lift nested inheritance transformer classes, add targeted unit tests, and wire them through the pipeline helper.
6. After refactor, re-run existing unit/integration suites to verify identical output; add focused tests for new helpers.

## Validation considerations
- Maintain existing transformation ordering to avoid regressions in idempotence tests.
- Ensure helper extractions preserve metadata dependencies (`PositionProvider`) by passing the transformer instance where needed.
- Guard new helpers with unit tests under `tests/unit/test_unittest_transformer_structure.py` (proposed) to confirm drop/keep decisions and fixture rendering.

## Open questions
- Should `debug_trace` be replaced by structured logging or dropped entirely once helpers provide clearer control flow?
- Are there opportunities to split the module into multiple files (e.g., `orchestration.py`, `helpers/module.py`)? Further analysis required after initial helper extraction.

## Next steps
- Draft an implementation plan (checklist) detailing helper extraction order, state encapsulation, and validation tasks.
- Schedule refactor work behind a short-lived feature branch to keep diffs reviewable and avoid merge conflicts with ongoing transformer updates.
