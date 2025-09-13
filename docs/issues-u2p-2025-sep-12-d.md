---
title: "u2p conversion evidence & issues — 2025-09-12 (run D)"
date: 2025-09-12
tags: [u2p, unittest-to-pytest, evidence, migration]
---

This file collects concrete evidence from a fresh conversion run (run D) of `splurge-unittest-to-pytest` executed on 2025-09-12. The goal was to revert tests, run the converter (with `--no-compat`), run pytest, and capture failures with exact diffs and snippets.

Commands executed
-----------------

- Revert tests to HEAD (worktree + index):

  git restore --source=HEAD --staged --worktree -- tests/

- Run converter with --no-compat and backups for run D:

  source .venv/Scripts/activate && splurge-unittest-to-pytest -r --no-compat -b backups/u2p-2025-09-12-d tests/

- Run pytest to execute converted tests:

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

- Backups saved to: `backups/u2p-2025-09-12-d/` (original files preserved with `.bak`)


Pytest run output (summary)
--------------------------

- Command: `pytest -q`
- Result: 147 passed, 2 failed
- Failing tests (first two failures shown by pytest):

  FAILED tests/unit/test_parameter_validation.py::TestParameterValidation::test_validation_with_nonexistent_table
  FAILED tests/unit/test_init_api.py::TestInitAPI::test_generate_class


Concrete evidence: git diff excerpts
-----------------------------------

Below are selective diffs showing key conversion changes that produced the problematic code.

1) `tests/unit/test_init_api.py` (partial diff / excerpt)

The converter added module-level pytest fixtures and an autouse attachment fixture. The problematic fixtures are self-referential:

@pytest.fixture
def sql_file():
    _sql_file_value = str(sql_file)
    return _sql_file_value

@pytest.fixture
def schema_file():
    _schema_file_value = str(schema_file)
    return _schema_file_value

These fixtures return strings like '<pytest_fixture(<function sql_file at 0x...>)>' which are then passed into tests that expect file paths.


2) `tests/unit/test_parameter_validation.py` (partial diff / excerpt)

The converter replaced `self.assertRaises(...)` with `pytest.raises(...)` but left the old attribute access in place:

    with pytest.raises(SqlValidationError) as cm:
        self.generator.generate_class(sql_fname, schema_file_path=schema_fname)

    error_msg = str(cm.exception)

In pytest the ExceptionInfo's wrapped exception is `cm.value`, not `cm.exception`. Accessing `cm.exception` raises AttributeError at runtime.


Concrete failing snippets (exact lines from converted files)
---------------------------------------------------------

- From `tests/unit/test_parameter_validation.py` (failing line):

    with pytest.raises(SqlValidationError) as cm:
        self.generator.generate_class(sql_fname, schema_file_path=schema_fname)

    error_msg = str(cm.exception)    # <-- AttributeError at runtime; should be cm.value

- From `tests/unit/test_init_api.py` (fixture excerpt):

@pytest.fixture
def sql_file():
    _sql_file_value = str(sql_file)
    return _sql_file_value

@pytest.fixture
def schema_file():
    _schema_file_value = str(schema_file)
    return _schema_file_value

These fixtures are incorrect and produce placeholder strings instead of paths.


Backups created during run D
---------------------------

Listing of `backups/u2p-2025-09-12-d` (top-level):

- test_cli.py.bak
- test_cli_end_to_end.py.bak
- test_cli_sql_type_option.py.bak
- test_code_generator.py.bak
- test_detect_statement_type.py.bak
- test_generate_types.py.bak
- test_init_api.py.bak
- test_parameter_validation.py.bak
- test_parse_sql_statements.py.bak
- test_remove_sql_comments.py.bak
- test_schema_parser.py.bak
- test_schema_parser_edge_cases.py.bak
- test_sql_parser.py.bak
- test_statement_detection.py.bak


Full pytest failure excerpt (what pytest printed)
------------------------------------------------

  E   AttributeError: 'ExceptionInfo' object has no attribute 'exception'
  File: tests/unit/test_parameter_validation.py:227

  E   FileNotFoundError: File not found: <pytest_fixture(<function sql_file at 0x...>)>
  File: tests/unit/test_init_api.py:62


Conclusion and recommended fixes
--------------------------------

The conversion produced two semantic issues:

1) Change `cm.exception` -> `cm.value` after `pytest.raises(...)`.
2) Rewrite broken `sql_file` and `schema_file` fixtures to actually create files (for example using `create_sql_with_schema`) and yield their paths, or remove those fixtures and let the class `setUp()` logic supply `self.sql_file` and `self.schema_file`.

Both fixes are small and localized. I can apply them and re-run pytest if you want — say the word and I'll implement the patches and report back with results.
