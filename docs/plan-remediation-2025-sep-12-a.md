---
title: "Plan: Remediation for u2p conversion issues — 2025-09-12 (run A)"
date: 2025-09-12
author: splurge-u2p-automation
---

Summary
-------

This document lists actionable remediation steps for the two failing tests observed after converting the test suite on 2025-09-12 (runs A and B). The failures are localized and caused by semantic mismatches between unittest idioms and pytest idioms introduced by the converter.

Historical note
---------------
The compatibility-mode and engine selection options (for example, `--no-compat` and `engine=`) were removed in release 2025.1.0. This plan documents remediation work performed before that change and is retained for historical context.

Summary


This document lists actionable remediation steps for the two failing tests observed after converting the test suite on 2025-09-12 (runs A and B). The failures are localized and caused by semantic mismatches between unittest idioms and pytest idioms introduced by the converter.
- Changes here are intentionally minimal and low-risk: fix the translated pytest usage and repair broken fixtures produced by the converter.

Root causes (short)
--------------------

1. `assertRaises` translation: converted tests access the caught exception via `cm.exception` (unittest idiom). In pytest the exception is `cm.value`.
2. Broken fixtures: the converter produced fixtures (`sql_file`, `schema_file`) that reference themselves (e.g., `str(sql_file)`) instead of creating and returning real file paths. This leads to FileNotFoundError when tests try to open the files.

Acceptance criteria / success conditions
----------------------------------------

- All tests in the converted suite run and pass locally (expected: pytest counts match pre-conversion coverage; i.e., 149 passed, 0 failed after fixes in the converted tests).
- The changes are minimal and isolated to the converted test files; they preserve test intent and readability.
- Changes include small tests that guard against regressions for the two patterns.

Remediation tasks (ordered)
---------------------------

Task 1 — Fix pytest.raises usage (low risk)

- Files to edit:
  - `tests/unit/test_parameter_validation.py`

- Change:
  - Replace uses of `cm.exception` with `cm.value` (the ExceptionInfo API in pytest).

- Rationale: aligns converted code with pytest ExceptionInfo semantics.

- Implementation notes:
  - Search for `cm.exception` usage pattern across the converted files and update all occurrences.
  - Add a tiny unit test (or assertion) that uses `pytest.raises` and asserts `excinfo.value` to prevent regression.

Task 2 — Repair broken fixtures that return placeholder repr (medium risk)

- Files to edit:
  - `tests/unit/test_init_api.py`

- Change:
  - Replace the generated `sql_file` and `schema_file` fixtures with concrete fixtures that create files on-disk and yield their paths. Use `tmp_path` (or `tmp_path`/`temp_dir` fixtures present in the test suite) and the helper `create_sql_with_schema` already referenced by the test code.
  - Ensure fixtures yield strings (not pathlib.Path objects) if the code under test expects str paths, or adapt to Path objects consistently.
  - Ensure cleanup is automatic via pytest (tmp_path is ephemeral); if helper creates files outside tmpdir, delete them in a finalizer.

- Example fixture pattern (conceptual):

    @pytest.fixture
    def sql_file(tmp_path, sql_content):
        sql_path, schema_path = create_sql_with_schema(tmp_path, "test.sql", sql_content)
        yield str(sql_path)

    @pytest.fixture
    def schema_file(tmp_path, sql_content):
        sql_path, schema_path = create_sql_with_schema(tmp_path, "test.sql", sql_content)
        yield str(schema_path)

- Rationale: Ensures tests receive real file paths instead of placeholder strings and prevents FileNotFoundError.

Task 3 — Run tests and verify locally (required)

- Commands (run inside the project venv):
  - Activate venv and run converter if needed (not required for these small edits):
    source .venv/Scripts/activate && splurge-unittest-to-pytest -r -b backups/ tests/
  - Run pytest:
    source .venv/Scripts/activate && pytest -q

- Expected result: tests previously failing now pass; overall test count should remain the same.

Task 4 — Add regression tests / CI checks (recommended)

- Add a tiny unit test in `tests/unit/` that demonstrates the correct use of `pytest.raises` and accesses `excinfo.value`. This guards against accidental future translations producing `cm.exception`.
- Add a test or lint rule verifying fixtures named `*_file` are actual Path/str-like objects and not placeholder repr strings. This can be a lightweight runtime assertion test in `tests/unit/test_conversion_smoke.py` that imports a converted test module and inspects its fixtures.
- Consider adding a small converter unit test in the converter's test suite that asserts translations of `assertRaises` produce `excinfo` usage that uses `.value` in the generated AST or text.

Task 5 — Code review and commit (required)

- Make the minimal edits in a dedicated branch (e.g., `fix/u2p-2025-09-12-exception-fixtures`).
- Run full pytest locally. If green, open a PR against `main` / or the working branch `2025.0.5` used for conversion.
- Include a brief PR description referencing `docs/issues-u2p-2025-sep-12-a.md` and `docs/issues-u2p-2025-sep-12-b.md` and link to this remediation plan.

Optional Task 6 — Enhancements to converter (medium effort)
-----------------------------------------------------------

- Improve the converter to:
  - When translating `assertRaises`, emit `with pytest.raises(...) as excinfo:` and update any access to `.exception` to `.value` when converting body code that references `cm.exception`.
  - For fixture generation: detect when a translated fixture references itself and instead rewrite the body to create and return a concrete artifact (e.g., use `tmp_path` or call known helper functions). This may require analysis of nearby `setUp` methods and helper calls.
- Add tests for the converter ensuring it handles these patterns.

Timeline and owners
-------------------

- Day 0 (same day): Implement Tasks 1–3 (edits + local test run). Owner: whoever has change rights (suggested: repo maintainer / PR author).
- Day 1: Open PR, include test updates, and request review. Owner: PR author.
- Day 2: Merge and monitor CI. Owner: reviewer / maintainer.

Risk and rollback
-----------------

- Changes are small and localized. If a fix introduces regressions, revert via git using the `.bak` files for reference or revert the commit.
- If any converter change (optional task 6) is large, do it in a feature branch with comprehensive tests.

Follow-ups (low-cost improvements)
----------------------------------

- Add the small regression tests and CI checks suggested above.
- Add a diagnostic check in the converter that emits a warning if a generated fixture contains a reference to itself (string like `'<pytest_fixture('`), so the user can inspect before running.
- Update conversion docs to list patterns that require manual review (e.g., `assertRaises` usages accessing `exception`, custom fixture creation logic, mocking of TestCase lifecycle methods).

Appendix: exact patch suggestions (examples)
-------------------------------------------

1) Replace `cm.exception` with `cm.value`:

- Search pattern: `cm.exception` -> `cm.value`

2) Example fixture replacement for `tests/unit/test_init_api.py`:

    @pytest.fixture
    def sql_file(tmp_path, sql_content):
        sql_path, schema_path = create_sql_with_schema(tmp_path, "test.sql", sql_content)
        yield str(sql_path)

    @pytest.fixture
    def schema_file(tmp_path, sql_content):
        sql_path, schema_path = create_sql_with_schema(tmp_path, "test.sql", sql_content)
        yield str(schema_path)


Status of plan tasks (todo list)
--------------------------------

- Task 1: not-started (will be executed if you request edits)
- Task 2: not-started
- Task 3: not-started
- Task 4: not-started


If you want, I can implement Tasks 1–3 now (make the edits, run pytest, and push a branch/PR). Reply with which actions you'd like me to take next.

Fixing the converter (implementation plan)
-----------------------------------------

Goal: Update `splurge-unittest-to-pytest` so converter output no longer requires manual edits for the two root causes above. Changes should be well-tested and backward-compatible for common patterns.

1) Modules to touch

- `splurge_unittest_to_pytest/stages/raises_stage.py` (or the module responsible for translating `assertRaises` patterns)
  - Behavior to implement: when converting a `TestCase.assertRaises` call into a pytest context manager, ensure generated code uses `with pytest.raises(ExpectedException) as excinfo:` and that any subsequent accesses to the caught exception in the converted body are rewritten from `.exception` -> `.value`.
  - Implementation approach: operate on the test AST (the project already uses AST-based rewrites in other stages). When you find a `with`-conversion from `assertRaises`, scan the converted block for attribute access nodes `Name('cm')` followed by `Attribute('.exception')` and rewrite the attribute to `.value` or remap the name used for the context manager variable.

- `splurge_unittest_to_pytest/converter/fixture_builder.py` or `splurge_unittest_to_pytest/converter/fixture_builders.py` (or `fixture_builder`/`fixture_function` modules)
  - Behavior to implement: detect self-referential fixture bodies that include references to the fixture's own name (e.g., `str(sql_file)` inside the `sql_file` fixture) and rewrite them into fixtures that actually construct the artifact (use `tmp_path` or call known helper factories like `create_sql_with_schema`).
  - Implementation approach: when generating a fixture, if the body trivially references the fixture name or a placeholder string, attempt to:
    - Identify helper calls used in the original TestCase `setUp` or test helpers (e.g., `create_sql_with_schema`) within the same module or nearby methods and call them instead inside the fixture body; or
    - Fall back to a conservative pattern: generate a fixture that accepts `tmp_path` and raises a clear runtime error pointing the maintainer to implement the fixture if converter cannot infer the helper usage automatically. Prefer the first option where helper calls are obviously present.

2) Tests to add (converter-level)

- `tests/unit/test_converter_raises_translation.py`
  - Input: a small unittest snippet using `assertRaises` and reading `cm.exception` inside the block.
  - Expectation: converter output contains `with pytest.raises(... ) as excinfo:` and subsequent code contains `excinfo.value` references.

- `tests/unit/test_converter_fixture_generation.py`
  - Input: a TestCase using `setUp()` to call `create_sql_with_schema` and tests that reference `self.sql_file` (or module-level fixtures that the converter previously produced incorrectly).
  - Expectation: converter emits a fixture `sql_file` that accepts `tmp_path` and yields a real path string, or at minimum emits a fixture that clearly calls the helper factory.

3) CI changes

- Ensure the repository's CI (GitHub Actions or similar) runs the converter unit tests when code touches conversion stages. Add a job/step `run-converter-tests` that runs pytest for `tests/unit/test_converter_*` with `-k converter` or explicit file paths.

4) Implementation constraints and safety

- Keep converter changes opt-in in behavior where ambiguity exists. If the converter cannot confidently infer how to build the fixture, it should leave a TODO comment in the generated test and emit a diagnostic warning rather than making an incorrect inference.
- Preserve backups (`.bak`) on conversion runs.
- Add logging/diagnostics so that future runs produce a compact summary of "patterns auto-fixed" vs "patterns requiring manual attention".

5) Rollout plan

- Implement changes behind a feature branch: `fix/u2p-converter-assertraises-fixtures`.
- Add the converter tests and run locally until green.
- Open PR, request review from maintainers.
- After merge, opt to run a fresh conversion on a representative suite (the tests used in earlier runs) and validate end-to-end results.

Notes and examples

- Example AST rewrite pseudo-step for `assertRaises`:
  - Detect `with self.assertRaises(SomeError) as cm:` or `self.assertRaises(SomeError, func, *args)` transformed into `with pytest.raises(SomeError) as excinfo:`. Then in the body rewrite `cm.exception` -> `excinfo.value`.

- Example fixture-generation heuristic:
  - If converter finds an assignment in `setUp()` like `self.sql_file, self.schema_file = create_sql_with_schema(...)`, prefer generating `sql_file` and `schema_file` fixtures that call `create_sql_with_schema(tmp_path, ...)` and yield proper values.

If you'd like I can begin implementation now: mark Task 2 (Implement converter fixes) as in-progress and make targeted edits to the suggested modules and add converter-level tests. Otherwise I can produce a PR-ready patch list for review first.