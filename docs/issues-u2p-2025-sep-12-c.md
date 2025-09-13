---
title: "u2p conversion analysis — 2025-09-12 (run C — new u2p version, --no-compat)"
date: 2025-09-12
tags: [u2p, unittest-to-pytest, migration, analysis]
---

Overview
--------

I installed an updated version of `splurge-unittest-to-pytest` and repeated the conversion process starting from a clean working tree. The conversion was run with the `--no-compat` flag and a dedicated backup directory. This document records the commands executed, the converter output, pytest results, and an analysis of failures and next steps.


Actions performed
-----------------

1) Restored previously-converted test files to `HEAD` to start from original tests.

2) Ran the newly installed converter with `--no-compat` and a fresh backup directory:

```bash
source .venv/Scripts/activate && \
  splurge-unittest-to-pytest -r --no-compat -b backups/u2p-2025-09-12-c tests/
```

This created backups under `backups/u2p-2025-09-12-c/` and converted the test files in-place.

3) Ran the test suite with pytest:

```bash
source .venv/Scripts/activate && pytest -q
```


Converter output (summary)
--------------------------

- Files processed: 14
- Files converted: 9
- Files unchanged: 5
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

- Backups saved to: `backups/u2p-2025-09-12-c/` (original files preserved with `.bak`)


Pytest results
--------------

- Run summary: 147 passed, 2 failed
- Failures are the same two that appeared in earlier runs (before upgrading the converter):
  1) tests/unit/test_parameter_validation.py::TestParameterValidation::test_validation_with_nonexistent_table
  2) tests/unit/test_init_api.py::TestInitAPI::test_generate_class

The new converter version did not change these outcomes.


Failure details and root cause analysis
--------------------------------------

1) tests/unit/test_parameter_validation.py::TestParameterValidation::test_validation_with_nonexistent_table

- Symptom: AttributeError: 'ExceptionInfo' object has no attribute 'exception'
- Explanation: The test uses a pytest raises context but accesses the caught exception as `cm.exception` (unittest convention). In pytest the correct attribute is `cm.value`.
- Fix: Replace `cm.exception` with `cm.value` in the converted tests that expect to inspect the exception object.


2) tests/unit/test_init_api.py::TestInitAPI::test_generate_class

- Symptom: FileNotFoundError: File not found: <pytest_fixture(<function sql_file at 0x...>)>
- Explanation: The converted fixtures `sql_file` and `schema_file` were generated incorrectly and reference themselves (e.g., `str(sql_file)`) rather than creating and returning real file paths. This causes pytest to pass a placeholder string as the fixture value, which then fails when code attempts to open the path.
- Fix: Replace the broken fixtures by implementing them to create files (e.g., call `create_sql_with_schema`), yielding actual file paths. Alternately, remove the module-level fixtures and rely on the class `setUp()` which already creates `self.sql_file` and `self.schema_file`.


Conclusions
-----------

- The newly installed version of `splurge-unittest-to-pytest` (run C) produced the same results as earlier attempts. The converter works for the majority of tests (147 passed) but requires small manual corrections for two tests where semantic translation from unittest to pytest wasn't fully resolved.
- The backups created in `backups/u2p-2025-09-12-c/` preserve the original test files if you prefer to inspect or revert.


Recommended next steps (I can perform these if you authorize me)
---------------------------------------------------------------

1) Apply the minimal fixes:

  - In `tests/unit/test_parameter_validation.py`: replace `cm.exception` with `cm.value` where appropriate.
  - In `tests/unit/test_init_api.py`: rewrite `sql_file` and `schema_file` fixtures to create files using `create_sql_with_schema` and yield their paths (use `temp_dir` fixture for cleanup), or remove the fixtures and use `self.sql_file`/`self.schema_file` from the class `setUp()`.

2) Re-run `pytest -q` to confirm all tests pass.

If you want me to implement these patches and re-run the suite, say so and I will make the edits and report back with the final test results and a short patch summary.
