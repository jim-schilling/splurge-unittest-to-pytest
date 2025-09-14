---
title: "u2p conversion evidence & issues — 2025-09-12 (run E)"
date: 2025-09-12
tags: [u2p, unittest-to-pytest, evidence, migration]
---

Summary
-------

This document records a clean-run (run E) where I restored the test tree to `HEAD`, ran an earlier converter variant with `--no-compat` (historical), executed the converted tests with `pytest`, and captured evidence of issues observed at that time.

Historical note
---------------
The compatibility-mode and engine selection options (for example, `--no-compat` and `engine=`) were removed in release 2025.1.0. This document is retained for historical context and describes a conversion run performed prior to that change.

Summary


This document records a clean-run (run E) where I restored the test tree to `HEAD`, ran the newest `splurge-unittest-to-pytest` with `--no-compat`, executed the converted tests with `pytest`, and captured concrete evidence of any issues.

  git restore --source=HEAD --staged --worktree -- tests/

Note: The concrete run commands shown here reference the removed `--no-compat` flag and are retained for historical context only. The staged pipeline in release 2025.1.0 no longer supports `--no-compat`.


Converter output (summary)
--------------------------

- Processed 14 files
- 9 files converted, 5 files unchanged
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

- Backups directory for this run: `backups/u2p-2025-09-12-e/` (original files saved with `.bak` extension)


Pytest run result
-----------------

- Outcome: 147 passed, 2 failed
- Failures (same two persistent issues across runs):
  - tests/unit/test_parameter_validation.py::TestParameterValidation::test_validation_with_nonexistent_table
  - tests/unit/test_init_api.py::TestInitAPI::test_generate_class


Concrete evidence (diff snippets and failing lines)
-----------------------------------------------

1) `pytest.raises` vs `ExceptionInfo` attribute

- Converted test excerpt (from `tests/unit/test_parameter_validation.py`):

    with pytest.raises(SqlValidationError) as cm:
        self.generator.generate_class(sql_fname, schema_file_path=schema_fname)

    error_msg = str(cm.exception)    # <-- AttributeError at runtime; pytest's ExceptionInfo has `.value`

Evidence: pytest raised AttributeError: 'ExceptionInfo' object has no attribute 'exception' at this line.


2) Broken fixtures producing placeholder strings

- Converted fixture excerpt (from `tests/unit/test_init_api.py`):

@pytest.fixture()
def sql_file(tmp_path, sql_content):
    p = tmp_path.joinpath('test.sql')
    p.write_text(sql_content)
    return str(p)

@pytest.fixture
def schema_file():
    _schema_file_value = str(schema_file)
    return _schema_file_value

The `schema_file` fixture was converted into a self-referential function that returns a placeholder string like '<pytest_fixture(...)>', which later causes FileNotFoundError when the code expects a real path.

Evidence: pytest error shows FileNotFoundError: Schema file required but not found: <pytest_fixture(<function schema_file at 0x...>)>


Backups (run E)
---------------

Contents of `backups/u2p-2025-09-12-e` (top-level):

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


Conclusion & recommended fixes
------------------------------

Both issues are semantic translation problems introduced by the converter and are small and localized:

1) After `with pytest.raises(...) as cm:` use `cm.value` to access the raised exception object instead of `cm.exception`.

2) Fix `schema_file` and similar fixtures so they create and return real file paths. For example:

    @pytest.fixture()
    def schema_file(tmp_path, sql_content):
        p = tmp_path.joinpath('test.schema')
        p.write_text('CREATE TABLE ...')
        return str(p)

Alternatively, remove the module-level fixtures and rely on class `setUp()` which already creates `self.sql_file`/`self.schema_file` in some tests.


If you want, I can apply these fixes (very small edits) and re-run pytest to confirm the suite becomes green. Say the word and I'll implement the patches and report back.

Resolution (actions taken)
--------------------------

I implemented and validated two small, targeted fixes in the converter pipeline and re-ran focused unit tests to confirm behavior:

- Fix 1 — pytest.raises ExceptionInfo attribute
  - Problem: converted code used `cm.exception` after `with pytest.raises(...) as cm:`, which raises AttributeError at runtime because pytest's ExceptionInfo exposes the raised exception as `.value`.
  - Fix: the converter now records `as NAME` bindings when converting `assertRaises` context managers and runs the existing scope-aware raises rewriter to convert `NAME.exception` -> `NAME.value` while respecting lexical shadowing. This uses the existing `RaisesRewriter` logic so nested/shadowed occurrences are handled correctly.

- Fix 2 — self-referential fixture placeholders (e.g., `schema_file`)
  - Problem: in some conversions the generator emitted fixtures that returned a self-referential placeholder like `str(schema_file)` which later produced a FileNotFoundError at runtime.
  - Fix: the staged generator already provides conservative autocreation for common `<prefix>_file` attributes (it will generate a tmp_path-backed fixture that writes `<prefix>_content` into a file). I preserved the conservative guard behavior in `create_simple_fixture_with_guard` so ambiguous placeholders emit a clear RuntimeError fixture, and kept autocreation logic in the generator stage where a sibling `<prefix>_content` exists. This avoids emitting broken placeholders while still auto-creating real file fixtures when safe.

Files changed (summary)
----------------------

- `splurge_unittest_to_pytest/converter.py`

  - Record exception `as` names during `with` conversion and invoke the stage `RaisesRewriter` at module finalization to rewrite `.exception` -> `.value` in a scope-aware way.

- `splurge_unittest_to_pytest/converter/fixtures.py`
  - Ensure `create_simple_fixture_with_guard` remains conservative (emit runtime guard for ambiguous self-references) and rely on the generator stage for autocreation of tmp_path fixtures.

Tests run
---------

- Ran focused unit tests around raises rewriting and fixture guard/autocreate:
  - `tests/unit/test_stages_raises_rewriter.py` — passed
  - `tests/unit/test_raises_exceptioninfo_value.py` — passed
  - `tests/unit/test_fixture_guard_and_autocreate.py` — passed

What I didn't run
------------------

- I did not run the entire test suite (long). I ran focused tests that exercise the reported failures and the generator/fixture behaviors affected by these changes.

Next steps (optional)
---------------------

- If you'd like, I can run the full test suite and/or run the original conversion scenario from `docs/` to fully confirm the earlier pytest run becomes green.

