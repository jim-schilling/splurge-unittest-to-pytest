# Plan: Support both `unittest` variants (FunctionTestCase and TestCase subclass)

Date: 2025-09-18
Author: (automated plan generated)

## Summary

This plan documents the analysis and implementation steps required to support converting two semantically-equivalent unittest module shapes into a single canonical pytest output. The two variants:

 - Variant A (new): module-level `unittest.FunctionTestCase(test_fn, setUp=..., tearDown=...)`. Example: `tests/unittest_pytest_samples/unittest_01_a.py.txt`.
 - Variant B (already supported): a `unittest.TestCase` subclass providing instance `setUp`, `tearDown`, and `test_*` methods. Example: `tests/unittest_pytest_samples/unittest_01_b.py.txt`.

Goal: ensure both variants convert to the same pytest output (target: `tests/unittest_pytest_samples/pytest_01.py.txt`).

## Small contract

- Input: a Python module using either FunctionTestCase or TestCase subclass patterns.
- Output: an idiomatic pytest module that:
  - Emits yield-style fixtures for resources created in `setUp` and cleaned in `tearDown`.
  - Emits top-level test functions (one per test method) accepting the fixture(s) as parameters.
  - Converts common `unittest` assertions into `assert` statements or pytest equivalents when safe.
- Error modes: when setup/teardown pairing is ambiguous, emit a conservative guarded fixture and produce a diagnostic for manual review.
- Success: both sample files above convert to the same `pytest_01.py.txt` and relevant unit tests pass.

## Analysis of Variant Differences (brief)

Variant A (FunctionTestCase):
  - `setUp` and `tearDown` are module-level functions.
  - Often assign to module-level variables (e.g., `_resource`) or otherwise mutate module state.
  - The converter does NOT yet fully normalize this pattern into the fixture pipeline; this plan adds a detector/normalizer so existing fixture generation can be reused.

- Variant B (TestCase subclass):
  - `setUp(self)` assigns to instance attributes (e.g., `self.resource = createResource()`).
  - `tearDown(self)` references and cleans the same instance attribute (e.g., `deleteResource(self.resource)`).
  - Test methods are instance methods (`def test_something(self):`) that use `self` attributes and `self.assertX` helpers.

## Detection / Matching spec

The converter must detect both patterns and normalize the data needed for fixture generation.

Detection rules:

 - FunctionTestCase pattern (new):
  - A call to `unittest.FunctionTestCase` (or `FunctionTestCase`) whose first positional argument is a function, and which has `setUp` / `tearDown` keyword args referring to module-level callables.
  - Note: `FunctionTestCase` may be referenced via aliases in real code. Examples to support:
    - `from unittest import FunctionTestCase as ftc` then `ftc(...)`
    - `ftc = FunctionTestCase` or `ftc = unittest.FunctionTestCase` followed by `ftc(...)`
    - `import unittest as ut` then `ut.FunctionTestCase(...)`
  - The collector must resolve such aliases by tracking imports and simple assignments at module scope so these call-sites are recognized as FunctionTestCase construction.

 - TestCase subclass pattern (existing):
  - A `ClassDef` whose bases include `unittest.TestCase` (or `TestCase` via `from unittest import TestCase`).
  - The class contains:
    - A `setUp` method where one or more assignments target `self.<attr>`.
    - Optionally, a `tearDown` method which references `self.<attr>` in cleanup calls.
    - One or more methods named with `test` prefix.

Normalized match output (example shape):

{
  "class_name": "TestSomething",
  "setup_assignments": { "resource": <libcst expression> },
  "teardown_cleanup": { "resource": [<list of libcst statements>] },
  "test_methods": [<FunctionDef nodes>],
  "original_node": <ClassDef node>
}

Notes: the converter already includes helpers to extract `setUp` assignments (`converter/setup_parser.py`) and to generate fixtures (`converter/fixtures.py`). The collector/stages must make this normalized output available to the fixtures stage.

## Transformation mapping (source -> target)

- For each attribute assigned in `setUp` (e.g., `self.resource = createResource()`):
  - Create a fixture named deterministically from the attribute (e.g., `resource` or `_resource_value` with name-collision avoidance). Prefer short, readable names.
  - Build fixture as yield-style if cleanup statements for that attribute exist. Fixture body:
    - bind the created value to a local variable
    - yield the value
    - perform cleanup statements with the attribute references replaced to the local variable

- For each `test_*` instance method:
  - Create a module-level function `def test_xxx(<fixture_params>):` where `<fixture_params>` is the list of fixtures created from the setUp assignment attributes. Use the project's current policy to either drop `self` and append fixture parameters (idiomatic pytest) or keep `self` and rely on autouse attach fixture for runnability; default preference: drop `self` and append fixtures.
  - Rewrite `self.<attr>` references in the test body into the bare fixture name (or local name selected by fixture creation helpers).
  - Convert `self.assertIsNotNone(x)` and similar to `assert` statements via existing assertion rewriters. If an assertion cannot be safely rewritten, preserve a functionally-equivalent form (e.g., call to `assert` or keep unittest call depending on risk).

- Remove the original `ClassDef` and its methods from output (the generated top-level functions and fixtures take the place of the class-based tests).

## Files and modules to modify

Primary places to review and modify:

- Collector and class detection
  - `splurge_unittest_to_pytest/stages/collector.py` (or whatever module provides `CollectorOutput`) — ensure the collector records:
    - `setup_assignments` for classes (re-using `converter/setup_parser.py`)
    - `teardown_cleanup` statements associated with attributes (use `converter/teardown_helpers.py` and `converter/cleanup_inspect.py` helpers).

- Fixtures stage tasks
  - `splurge_unittest_to_pytest/stages/fixtures_stage_tasks.py` — BuildTopLevelTestsTask already rewrites class methods to top-level functions and rewrites `self.attr` to `attr`. Ensure it is wired to use the collector's recorded `setup_assignments` and `teardown_cleanup` so fixture nodes can be created and injected.
  - `splurge_unittest_to_pytest/stages/fixtures_stage.py` — orchestrates the stage; ensure the `pattern_config` detection respects setUp/tearDown naming if customized.

- Fixture creation helpers (already present)
  - `splurge_unittest_to_pytest/converter/setup_parser.py` — parses assignments in `setUp` (already exists and can be reused).
  - `splurge_unittest_to_pytest/converter/fixtures.py` — helpers such as `create_fixture_with_cleanup` and `create_simple_fixture` exist and should be used rather than reinventing fixture nodes.
  - `splurge_unittest_to_pytest/converter/fixture_builder.py`, `simple_fixture.py`, `name_replacer.py` — utilities for name replacement and collision avoidance.

- Teardown inspection
  - `splurge_unittest_to_pytest/converter/teardown_helpers.py` and `cleanup_inspect.py` — locate and extract cleanup statements referencing `self.<attr>` so they can be placed in fixture cleanup.

- Assertion rewrites (existing)
  - `splurge_unittest_to_pytest/converter/assertions.py` and `assertion_dispatch.py` — used to convert `self.assertX` into pytest-style assertions.

- Tests
  - Add unit/integration tests under `tests/unit/` and/or `tests/integration/` referencing `tests/unittest_pytest_samples/unittest_01_b.py.txt` and golden `tests/unittest_pytest_samples/pytest_01.py.txt`.

Stage-1: Collector updates (detection)
- Task 1.0: Add detection for `FunctionTestCase` call-sites. Parse `setUp`/`tearDown` keyword args and resolve them to module-level function definitions. Normalize this data into the same structure used for class-based tests so the fixtures stage can consume it.
- Task 1.1: Extend collector to record per-class `setup_assignments` (use `parse_setup_assignments`).
- Task 1.2: Extend collector to record `teardown_cleanup` for attributes that appear in `tearDown`.
- Acceptance: Collector outputs a normalized representation for both `unittest_01_a.py.txt` and `unittest_01_b.py.txt` containing attribute names, create expression, cleanup statements, and test methods.

- Task 2.1: Use `create_fixture_for_attribute` / `create_fixture_with_cleanup` to generate fixture nodes from collector data.
- Task 2.2: Ensure fixtures are inserted into the module before test functions (use fixture-injector stage logic).
- Task 2.3: Use `BuildTopLevelTestsTask` to flatten test methods into top-level functions and append fixture params (or rely on autouse attach if policy chooses to keep `self`).
- Acceptance: Converted module contains fixture(s) and top-level test functions; `self.<attr>` references are replaced with fixture param names.
Stage-3: Assertion conversions & final tidy
- Task 3.1: Run assertion rewriter stage to convert `self.assertX` usages.
- Task 3.2: Run module tidy stage to add `import pytest` when needed and to reformat spacing.
- Acceptance: Conversions match project formatting and import policies.

Stage-4: Tests & docs
- Task 4.1: Add unit tests that run the pipeline on both sample files and compare to golden `pytest_01.py.txt`.
- Task 4.2: Run full test suite locally, fix any regressions revealed by lint/type checks.
- Task 4.3: Add a short note to `docs/` explaining both variants are supported and highlighting the conversion strategy.
## Edge cases and decisions

- Conditional or complex teardown: include the teardown statements as-is inside the fixture cleanup but rewrite `self.<attr>` references to the fixture-local name. If cleanup references multiple attributes, preserve the statements and substitute accordingly.
- If the converter cannot infer a safe fixture (e.g., `self.x = x` where `x` is a module-level name), emit a guarded fixture that raises a clear runtime error explaining the ambiguity.
- If tests rely heavily on `self` for runtime behaviour beyond attribute storage (rare), provide an autouse attach fixture fallback to keep the class methods runnable (project already supports autouse attach glue).
 - Aliased `FunctionTestCase` names: ensure the collector recognizes common aliasing patterns:
   - `from unittest import FunctionTestCase as ftc`
   - `ftc = FunctionTestCase` or `ftc = unittest.FunctionTestCase`
   - `import unittest as ut` then `ut.FunctionTestCase`
   The acceptance criteria: a call expression whose callee resolves (via imports and simple assignments) to the original `unittest.FunctionTestCase` should be treated identically to a direct `FunctionTestCase(...)` call. If resolution fails (e.g., dynamic assignment), emit a diagnostic and skip automatic normalization.

## Testing strategy

- Unit tests for collector and parser:
  - Test `parse_setup_assignments` on the `unittest_01_b.py.txt` sample and assert mapping contains the expected attribute/value AST.
  - Test teardown detection helpers return cleanup statements referencing the attribute.

- Golden conversion tests:
  - A test that runs the full pipeline on `unittest_01_a.py.txt` and `unittest_01_b.py.txt` and asserts exact equality with `pytest_01.py.txt`.

- Integration smoke:

- Both `tests/unittest_pytest_samples/unittest_01_a.py.txt` and `tests/unittest_pytest_samples/unittest_01_b.py.txt` convert to the same `tests/unittest_pytest_samples/pytest_01.py.txt`.
- Unit tests covering the new detection/transform are added and pass.
- No new linter or mypy failures are introduced by the changes (or they are fixed before merge).

## Timeline (estimate)

- Collector changes and detection tests: 1–2 hours
- Fixture creation & flattening implementation: 1–2 hours
- Add golden tests and run pipeline: 30–60 minutes
- Fix lint/type issues and finalize docs: 30–90 minutes

## Security and safety notes

- No external network calls are needed. The converter manipulates ASTs only.
- When emitting runtime guards, ensure error messages don't leak secrets (none expected here).

## Recent changes (tracking)

- Working branch: `feature/update-2025.3.1` has been created and checked out for this work.
- Project todo tracker: detection for FunctionTestCase (Variant A) has been marked in-progress.

## Next steps (immediate)

1. Implement detection and normalization for `FunctionTestCase` call-sites (Variant A) so the collector emits the same normalized representation used for class-based tests; add unit tests asserting the normalized shape for `unittest_01_a.py.txt`.
2. Wire fixture generator stage to consume the collector's new data and emit fixture nodes using `create_fixture_for_attribute` (reuse existing helpers).
3. Add golden conversion tests to assert exact output equality for both variants and run the targeted tests.

## Todo mapping (current tracker)

- Analyze 'b' variant AST and differences — completed
- Add detection of FunctionTestCase 'b' pattern — in-progress (collector changes)
- Transform setUp/tearDown into a pytest fixture — not started
- Add unit/integration tests for conversion — not started
- Run test suite, linters and fix issues — not started
- Update README/docs and add example note — not started


---

File references mentioned in this plan:
- `tests/unittest_pytest_samples/unittest_01_a.py.txt`
- `tests/unittest_pytest_samples/unittest_01_b.py.txt`
- `tests/unittest_pytest_samples/pytest_01.py.txt`

Implementation helper modules (already present in repo):
- `splurge_unittest_to_pytest/converter/setup_parser.py`
- `splurge_unittest_to_pytest/converter/fixtures.py`
- `splurge_unittest_to_pytest/stages/fixtures_stage_tasks.py`
- `splurge_unittest_to_pytest/converter/teardown_helpers.py`



