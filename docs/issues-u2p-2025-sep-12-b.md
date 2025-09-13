---
title: "u2p conversion analysis — 2025-09-12 (run B — --no-compat)"
date: 2025-09-12
tags: [u2p, unittest-to-pytest, migration, analysis]
---

Summary
-------

This document records a second conversion attempt where the `splurge-unittest-to-pytest` converter was run with the `--no-compat` flag (disables the compatibility autouse fixture). The goal was to avoid the converter attaching fixtures to unittest-style instances, and to see whether that resolves earlier issues.

Commands executed
-----------------

- Revert any previously converted tests to HEAD (left backups in the previous `backups/` location untouched).
- Run converter (from project root):

  source .venv/Scripts/activate && splurge-unittest-to-pytest -r --no-compat -b backups/u2p-2025-09-12-b tests/

- Run pytest:

  source .venv/Scripts/activate && pytest -q


Converter output (summary)
--------------------------

- Processed 14 files
- 9 files converted, 5 unchanged
- Converted files (modified in working tree):
  - tests/integration/test_cli.py
  - tests/integration/test_cli_sql_type_option.py
  - tests/unit/test_code_generator.py
  - tests/unit/test_generate_types.py
  - tests/unit/test_init_api.py
  - tests/unit/test_parameter_validation.py
  - tests/unit/test_schema_parser.py
  - tests/unit/test_schema_parser_edge_cases.py
  - tests/unit/test_sql_parser.py

- Backups created under `backups/u2p-2025-09-12-b/` (original files preserved with `.bak`).


Pytest run results
------------------

- Command: `pytest -q`
- Outcome: 147 passed, 2 failed (same two failures observed previously)


Failures (same root causes)
---------------------------

1) `tests/unit/test_parameter_validation.py::TestParameterValidation::test_validation_with_nonexistent_table`

- Failure: AttributeError: 'ExceptionInfo' object has no attribute 'exception'
- Cause: The converter produced `pytest.raises` usage but the test code still accessed `cm.exception` (unittest idiom). In pytest, the caught exception is `cm.value`.

2) `tests/unit/test_init_api.py::TestInitAPI::test_generate_class`

- Failure: FileNotFoundError referencing `<pytest_fixture(<function sql_file ...>)>`
- Cause: Broken fixture definitions — the converted fixtures for `sql_file` and `schema_file` reference themselves (e.g., `str(sql_file)`) instead of creating and returning actual file paths. This results in pytest passing a placeholder fixture repr string into tests that expect a real path.


Analysis and notes
------------------

- Running with `--no-compat` removed the compatibility autouse fixture behavior, but it did not resolve the two failures. These two issues are semantic; they require small manual fixes in the converted test code:
  - Replace `cm.exception` with `cm.value` where tests expect the underlying exception object.
  - Replace or reimplement the broken `sql_file`/`schema_file` fixtures so they actually create files and yield their paths (or remove them and rely on class `setUp()` logic).

- The majority of converted tests (147) pass, which indicates the conversion is largely successful. The remaining changes are targeted and small.


Recommendations
---------------

Apply the following minimal edits and re-run tests:

1. `tests/unit/test_parameter_validation.py` — change `cm.exception` -> `cm.value`.

2. `tests/unit/test_init_api.py` — replace broken fixtures with working ones that call `create_sql_with_schema` and yield paths; ensure cleanup is handled by the `temp_dir` fixture.

If you want, I can make these minimal edits and re-run the test suite and commit the changes for you.


Artifacts
---------

- Converted test files in working tree (see list above).
- Backups in:
  - `backups/` (original run A)
  - `backups/u2p-2025-09-12-b/` (run B — --no-compat)


Status
------

Conversion run B completed; issues remain in two converted tests caused by semantic mismatches between unittest and pytest idioms. These require small manual fixes.
