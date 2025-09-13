---
title: "u2p conversion remediation plan — 2025-09-12 (run C)"
date: 2025-09-12
tags: [u2p, remediation, unittest-to-pytest]
---

Summary
-------

This document captures the remediation steps for the latest conversion run (run C). The converter successfully translated the majority of tests, but two converted tests are failing with semantic issues:

- Attribute access to a caught exception uses `cm.exception` (unittest) but should use `cm.value` (pytest ExceptionInfo.value).
- Converter-produced fixtures for file-like artifacts (`sql_file`, `schema_file`) are self-referential placeholders and must be implemented to create and return actual file paths.

Goals
-----

1. Fix the converter so future conversions do not require manual edits for these patterns.
2. Provide small, minimal manual-change suggestions for already-converted tests to get green quickly.
3. Add unit tests to prevent regressions and run them in CI.

Immediate manual fixes (quick path)
---------------------------------

Apply these minimal edits to the converted tests and re-run pytest to get a green suite quickly.

1) Replace `cm.exception` -> `cm.value` in converted tests that used unittest's context-manager exception capture. Example:

   - Before: with pytest.raises(ValueError) as cm: ...; e = cm.exception
   - After:  with pytest.raises(ValueError) as cm: ...; e = cm.value

   Files to edit (examples from run B):
   - `tests/unit/test_parameter_validation.py::TestParameterValidation::test_validation_with_nonexistent_table`

2) Replace or implement fixtures that are placeholders for file artifacts. For each converted fixture like `sql_file` or `schema_file` that currently returns a placeholder string, implement it so it creates the needed file(s) and yields their paths (using `tmp_path`), e.g.:

   @pytest.fixture
   def sql_file(tmp_path):
       p = tmp_path / "schema.sql"
       p.write_text("-- SQL for tests")
       yield str(p)

   Use helper factory functions where available (e.g., `create_sql_with_schema`) if the project provides them.

   Files to edit (example):
   - `tests/unit/test_init_api.py::TestInitAPI::test_generate_class`

Converter fixes (longer-term, source changes)
-------------------------------------------

Make the converter robust so these edits are automatic for future runs. Proposed changes (low-risk, incremental):

1) Robust ExceptionInfo attribute rewrite

   - Problem: converting `with self.assertRaises(Exception) as cm:` to `with pytest.raises(Exception) as cm:` is not sufficient; attribute access to the captured exception must change from `cm.exception` to `cm.value`.
   - Fix: update the raises-stage transformer to record context-manager `as` names when it replaces assertRaises. After or during module traversal, rewrite attribute accesses `NAME.exception` -> `NAME.value` for recorded names. Keep the original name (e.g., `cm`) so test readability is preserved.
   - Tests: add unit tests that feed small modules to the transformer and assert the generated code contains `cm.value` instead of `cm.exception`.

2) Safer fixture generation for file-like attributes

   - Problem: when the converter cannot infer how to build an artifact (e.g., `self.sql_file = sql_file` placeholder), the naive fixture returns a reference to itself or a placeholder instead of creating the resource.
   - Fix approach (conservative): when a setup assignment is a trivial placeholder (a bare name equal to the attribute or `self.attr`), the converter should emit a guard fixture that raises a clear RuntimeError at test collection or generate a small fixture that uses `tmp_path` to create a minimal artifact. Prefer the guard if semantic inference is ambiguous; prefer auto-creation only when a safe default is possible.
   - Implementation details:
     - Detect placeholder patterns at AST level (cst.Name with same identifier, or cst.Attribute with `self`/`cls`).
     - For ambiguous placeholders: generate a fixture that raises a RuntimeError with an informative message linking to the remediation plan and suggesting `tmp_path` usage.
     - For clear patterns where a small file will suffice, generate a fixture that creates a file under `tmp_path` and yields the path as a string. Use project helper functions if available.
   - Tests: add unit tests for both guard and auto-created fixture cases. Use `cst` unit tests to assert fixture source and integration tests using pytest and tmp_path to assert fixtures created a real file.

3) Diagnostics and converter flags

   - Add a diagnostic warning emitted during conversion when placeholders are detected. Provide a `--auto-create` flag to enable best-effort artifact creation for file-like placeholders (default: off).
   - Document the flag behavior in `README-DETAILS.md` and in the converter `--help` output.

Verification steps
------------------

1. Add unit tests covering the two fixes (attribute rewrite + fixture guard/creation). Run them locally.
2. Run the converter on the sample repository or the set of test files used in run B (the same set that produced 147 passing and 2 failing). The converter should not produce the two reported failures.
3. Run pytest and ensure all tests pass.

CI and process updates
----------------------

- Add a converter-specific job in CI that runs the new unit tests and the converter on a small representative sample of files (or the project's own tests in a job matrix). This will prevent regressions.
- Add the remediation plan as an artifact or link in the PR when the feature branch is opened.

Next steps I can take
---------------------

- I can apply the minimal manual edits to the two failing converted tests and re-run pytest to get a green suite quickly (low effort).
- I can implement the converter changes and add the unit tests described above; once done I'll run the full unit test suite and prepare a PR.

Status of related todos
-----------------------

- Minimal manual fixes: quick and actionable (recommended for immediate green builds).
- Converter changes: medium risk but high value — add tests and CI coverage to prevent regressions.

Appendix
--------

Files mentioned in the run B report (converted):

- tests/unit/test_parameter_validation.py
- tests/unit/test_init_api.py
- backups/u2p-2025-09-12-b/
