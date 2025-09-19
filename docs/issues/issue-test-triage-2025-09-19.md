# Issue: Test triage — 2025-09-19

Summary
------
This issue captures the failing tests observed when running the full test suite on branch `feature/update-2025.3.1` (run: `pytest -n 7 -q`).

Test run snapshot
-----------------
- Command: pytest -n 7 -q
- Result: 37 failed, 1071 passed, 5 skipped, 1 xfailed, 12 warnings
- Run time: ~17.7s on Windows, Python 3.12.10

Master checklist (failing tests)
-------------------------------
- [ ] tests/unit/test_core_0001.py::TestClassStructure::test_setup_method_conversion
    - Category: triage
    - Priority: High
    - Symptom: Converted output is missing an `@pytest.fixture` function for the setUp; top-level tests are receiving fixture args but fixture definition not emitted.

- [ ] tests/unit/test_core_0001.py::TestClassStructure::test_teardown_method_conversion
    - Category: triage
    - Priority: High
    - Symptom: tearDown->fixture yield not emitted as a fixture declaration (missing `@pytest.fixture`).

- [ ] tests/unit/test_core_0001.py::TestClassStructure::test_setup_teardown_fixture_integration
    - Category: triage
    - Priority: High
    - Symptom: Expect yield fixture and fixture function with proper cleanup; currently only parameterized tests show up, fixture function missing.

- [ ] tests/unit/test_core_0001.py::test_converted_fixtures_return_paths
    - Category: triage
    - Priority: Medium
    - Symptom: Converter output missing helper fixture `sql_file` definition; tests reference the expected fixture.

- [ ] tests/unit/test_core_0001.py::TestClassStructure::test_teardown_triggers_yield_fixture_for_temp_dir
    - Category: triage
    - Priority: High
    - Symptom: Expected `temp_dir` fixture function with yield; missing.

- [ ] tests/unit/test_exceptions_main_0001.py::TestEdgeCases::test_convert_empty_file
    - Category: triage
    - Priority: Medium
    - Symptom: Empty file should be a no-op; converter now adds `import pytest` causing has_changes=True.

- [ ] tests/unit/test_exceptions_main_0001.py::TestEdgeCases::test_convert_file_whitespace_only
    - Category: triage
    - Priority: Medium
    - Symptom: Whitespace-only input should not be modified; converter appended `import pytest`.

- [ ] tests/unit/test_core_0001.py::TestComplexScenarios::test_complete_test_class_conversion
    - Category: triage
    - Priority: High
    - Symptom: Multiple tests expected to share a fixture (decorated function) but only parameterized tests without fixture decl are present.

- [ ] tests/unit/test_core_main_0001.py::test_init_api_rhs_preserved
    - Category: triage
    - Priority: Medium
    - Symptom: Expected `yield _InitAPIData(str(sql_file), str(schema_file))` in the converted fixture; missing — likely related to fixture generation or ordering.

- [ ] tests/unit/test_main_0002.py::test_autouse_fixture_accepts_fixture_params_and_attaches
    - Category: triage
    - Priority: High
    - Symptom: Expected fixture `x` emitted; converter passes `x` into test but fixture def absent.

- [ ] tests/unit/test_main_0002.py::test_import_pytest_not_added_when_unused
    - Category: triage
    - Priority: Medium
    - Symptom: Converter adds `import pytest` even when no pytest constructs (fixtures/decorators) are present.

- [ ] tests/unit/test_main_0002.py::test_fixture_creation_delegation_simple_and_attribute
    - Category: triage
    - Priority: High
    - Symptom: Fixture `x` expected to be declared; only parameterized test present.

- [ ] tests/unit/test_main_0002.py::test_convert_setup_to_fixture_creates_assignments_and_fixtures
    - Category: triage
    - Priority: High
    - Symptom: setUp->fixture conversion not producing fixture def.

- [ ] tests/unit/test_main_2.py::test_fixture_with_multiple_cleanup_statements
    - Category: triage
    - Priority: High
    - Symptom: Multiple setup attrs (d, f) should produce fixture functions; not emitted.

- [ ] tests/unit/test_main_0002.py::test_transformer_emits_guard_fixture_for_self_referential_setup
    - Category: triage
    - Priority: High
    - Symptom: self.sql_file = sql_file should create a guard fixture for sql_file; fixture def missing.

- [ ] tests/unit/test_main_0002.py::test_complex_teardown_pattern
    - Category: triage
    - Priority: High
    - Symptom: Conditional cleanup in tearDown expected to be preserved in fixture teardown; missing.

- [ ] tests/unit/test_main_0002.py::test_pytest_import_inserted_before_fixtures
    - Category: triage
    - Priority: Medium
    - Symptom: Tests expect `import pytest` to appear before any `@pytest.fixture` declarations; currently either fixture decorators missing or ordering wrong.

- [ ] tests/unit/test_main_0003.py::test_multiple_setup_attributes_produce_multiple_fixtures
    - Category: triage
    - Priority: High
    - Symptom: Multiple setup attributes not producing separate fixture functions; tests only show parameterized test args.

- [ ] tests/unit/test_main_0003.py::test_autouse_fixture_accepts_fixture_params_and_attaches
    - Category: triage
    - Priority: High
    - Symptom: Fixture `x` not emitted; test only shows parameter usage.

- [ ] tests/unit/test_main_0003.py::test_variable_name_consistency
    - Category: triage
    - Priority: Medium
    - Symptom: Variable `tables` expected fixture def; missing.

- [ ] tests/unit/test_main_0003.py::test_import_pytest_not_added_when_unused
    - Category: triage
    - Priority: Medium
    - Symptom: Same as earlier: `import pytest` added when unused.

- [ ] tests/unit/test_main_0003.py::test_converter_emits_pytest_import_and_autouse_fixture
    - Category: triage
    - Priority: High
    - Symptom: Expected `def temp_dir(...)` fixture function and autouse usage; fixture def missing.

- [ ] tests/unit/test_main_0003.py::test_fixture_creation_delegation_simple_and_attribute
    - Category: triage
    - Priority: High
    - Symptom: Fixture `x` expected but missing.

- [ ] tests/unit/test_main_0003.py::test_fixture_with_multiple_cleanup_statements
    - Category: triage
    - Priority: High
    - Symptom: Multiple cleanup fixtures expected; missing.

- [ ] tests/unit/test_main_0003.py::test_convert_setup_to_fixture_creates_assignments_and_fixtures
    - Category: triage
    - Priority: High
    - Symptom: Missing fixture function `x`.

- [ ] tests/unit/test_main_0003.py::test_complex_teardown_pattern
    - Category: triage
    - Priority: High
    - Symptom: Conditional cleanup missing in converted fixture.

- [ ] tests/unit/test_main_0003.py::test_pytest_import_inserted_before_fixtures
    - Category: triage
    - Priority: Medium
    - Symptom: Ordering of pytest import vs fixtures not as expected (fixture decorators missing).

- [ ] tests/unit/test_main_0003.py::test_transformer_emits_guard_fixture_for_self_referential_setup
    - Category: triage
    - Priority: High
    - Symptom: Missing fixture `sql_file` def.

- [ ] tests/unit/test_main_0002.py::test_fixture_with_cleanup_yield_pattern
    - Category: triage
    - Priority: High
    - Symptom: `temp_dir` yield-style fixture missing.

- [ ] tests/unit/test_pipeline_stages_0001.py::test_pipeline_runs_all_stages_and_inserts_fixtures_and_import
    - Category: triage
    - Priority: High
    - Symptom: Pipeline expected to insert one fixture function (`r`) and a single pytest import; none found.

- [ ] tests/integration/test_sample06_conversion_0001.py::test_sample_06_matches_golden
    - Category: triage
    - Priority: Medium
    - Symptom: Golden differs only by an extra `import pytest` and missing fixture declarations/order. Needs targeted diff.

- [ ] tests/integration/test_unittest_sample_01_conversion_0001.py::test_unittest_01_a_converts_to_golden
    - Category: triage
    - Priority: High
    - Symptom: Expected fixture `resource` declaration with docstring and yield; actual has parameter `_resource` and no fixture def.

- [ ] tests/integration/test_unittest_sample_01_pipeline_0001.py::test_unittest_01_a_pipeline_converts_to_golden
    - Category: triage
    - Priority: High
    - Symptom: Same golden mismatch as above in pipeline end-to-end path.


Analysis & grouping
-------------------
From the failing set the issues group into a few clear buckets:

1) Fixture emission/insertion missing (High priority)
   - Symptoms: Many tests show converted tests accepting fixture names as function args, but the corresponding `def <name>(...):` fixture definitions with `@pytest.fixture` are missing from output. Examples: tests that expect `def x`, `def temp_dir`, `def resource`, `def sql_file`, etc.
   - Likely root causes:
     - BuildTopLevelTestsTask creates fixtures in-memory but the fixture-injector stage may not be receiving/placing them.
     - Or the fixtures are created but filtered/removed by later pipeline stages (tidy/remove artifacts/import injector ordering).
   - Immediate remediation: trace the TaskResult delta produced by BuildTopLevelTestsTask (ensure it includes `fixture_nodes`), then trace fixture_injector to ensure it consumes `fixture_nodes` and inserts them before test functions.

2) Pytest import insertion behavior (Medium priority)
   - Symptoms: `import pytest` added to modules even when no pytest constructs remain; or ordering of import vs fixtures not matching tests.
   - Likely root causes:
     - Import injection runs when `needs_pytest_import` flag is set in a stage delta, but that flag may be set too eagerly (e.g., when fixtures are built but not actually injected), or import-injector runs before fixture insertion.
   - Immediate remediation: verify `needs_pytest_import` only set when fixture_nodes are present and ensure import_injector runs after fixture injection or uses presence of `@pytest.fixture` nodes in final module to decide.

3) Empty/whitespace-only file conversion (Medium priority)
   - Symptoms: Empty or whitespace-only inputs are altered by adding `import pytest` — tests expect no changes.
   - Likely root cause: some insertion logic unconditionally adds `import pytest` when `needs_pytest_import` is set in context even if module has no content; or pipeline stages run with default flags.
   - Immediate remediation: make import injection conditional on final presence of pytest usages (decorators or fixtures) or avoid marking `has_changes` for empty input.

4) Golden mismatch (Medium/High priority)
   - Symptoms: Integration golden files mismatch due to missing fixture definitions and ordering; these are symptomatic of (1) and (2).
   - Immediate remediation: fix (1) and (2), rerun golden tests.

Prioritization recommendation
---------------------------
- P0 (fix immediately):
  - Fixture emission/insertion pipeline bug (tests referencing fixture definitions: missing `def <name>` and decorators). These are core regressions (affect many tests & golden outputs).
  - Pipeline stage coordination: ensure BuildTopLevelTestsTask → fixture_injector → import_injector ordering and flags are consistent.

- P1 (high but secondary):
  - `import pytest` insertion behavior (avoid adding when unused; ordering vs fixtures).
  - Empty/whitespace-only file - preserve no-op behavior.

- P2 (lower):
  - Sample/golden diffs once P0/P1 fixed; re-run full suite and iterate on formatting/details.

Next concrete steps (suggested)
------------------------------
1. Reproduce minimal failing case locally (done via pytest output). Pick a representative unit test such as:
   - `tests/unit/test_main_0002.py::test_convert_setup_to_fixture_creates_assignments_and_fixtures`
   - or `tests/unit/test_pipeline_stages_0001.py::test_pipeline_runs_all_stages_and_inserts_fixtures_and_import`
   Run them with -q to trace outputs.

2. Instrument the `BuildTopLevelTestsTask.execute()` to log/attach a simple diagnostic to the task result delta showing number and names of `fixture_nodes` produced.

3. Instrument `fixture_injector` stage to log whether it receives `fixture_nodes` and what it inserts.

4. Ensure `needs_pytest_import` is only set when `fixture_nodes` non-empty OR a final presence check of `@pytest.fixture` nodes succeeds.

5. Re-run the focused tests and observe whether fixture functions now appear in converted output and whether `import pytest` is placed correctly.

Owners / Notes
--------------
- Primary owner (initially): current branch maintainer (you) or me — I can start step (2) and (3) to trace the flow unless you prefer to do it locally.
- Keep changes minimal and targeted: prefer logging and small checks rather than broad rewrites.

If you'd like I can now:
- Start triaging P0 by adding minimal logging/diagnostics in `BuildTopLevelTestsTask` and `fixture_injector` and re-run the focused failing tests, or
- Open a draft PR containing the triage doc only.

