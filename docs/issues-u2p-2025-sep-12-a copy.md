---
title: "u2p conversion analysis — 2025-09-12 (run A)"
date: 2025-09-12
tags: [u2p, unittest-to-pytest, migration, analysis]
---

Summary
-------

I ran the `splurge-unittest-to-pytest` converter (from the project's `.venv`) against the repository `tests/` directory on 2025-09-12. Conversion was executed with backups enabled; the converter created `.bak` backups in `backups/`.

Key outcomes
------------

- Conversion command used (from project root):

  source .venv/Scripts/activate && splurge-unittest-to-pytest -r -b backups/ tests/

- Converter output (summary):
  - Processed 14 files
  - 9 files converted, 5 files unchanged

- Backups were created under `backups/` (examples):
  - `backups/test_init_api.py.bak`
  - `backups/test_parameter_validation.py.bak`
  - `backups/test_generate_types.py.bak`
  - (full list present under `backups/`)

- Tests were executed with pytest after conversion:
  - Command used: `pytest -q` (run inside the same venv)
  - Result: 147 passed, 2 failed


Files converted (modified in working tree)
----------------------------------------

- tests/integration/test_cli.py
- tests/integration/test_cli_sql_type_option.py
- tests/unit/test_code_generator.py
- tests/unit/test_generate_types.py
- tests/unit/test_init_api.py  <-- failing
- tests/unit/test_parameter_validation.py  <-- failing
- tests/unit/test_schema_parser.py
- tests/unit/test_schema_parser_edge_cases.py
- tests/unit/test_sql_parser.py


Failures and causes (detailed)
------------------------------

Two converted tests failed when running pytest. Both failures appear to be caused by imperfect translations of unittest idioms to pytest idioms.

1) tests/unit/test_parameter_validation.py::TestParameterValidation::test_validation_with_nonexistent_table

- Symptom: AttributeError: 'ExceptionInfo' object has no attribute 'exception'
- Root cause: The converter changed the unittest `assertRaises` usage into pytest's `raises` context manager but left the code that accessed the caught exception as `cm.exception`. In pytest the context manager returns an `ExceptionInfo` whose wrapped exception is available as `cm.value` (not `cm.exception`).
- Minimal fix: replace `cm.exception` with `cm.value` in the converted tests where appropriate.


2) tests/unit/test_init_api.py::TestInitAPI::test_generate_class

- Symptom: FileNotFoundError: File not found: <pytest_fixture(<function sql_file at 0x...>)>
- Root cause: The converter generated broken fixtures for `sql_file` and `schema_file`. The fixture code references itself (for example `str(sql_file)`) instead of creating or returning a real filename/path. That leads pytest to pass a placeholder fixture repr string into the test, and code that expects a real path fails when trying to open the file.
- Minimal fix: Replace the broken fixture bodies with fixtures that actually create the files (for example, call the helper `create_sql_with_schema` inside the fixture and yield the created filenames). Alternatively, remove the module-level fixtures and use the class' `setUp()`/instance attributes.


Notes about the converter behavior
---------------------------------

- The converter did a reasonable job overall — 147 tests passed after conversion without any code changes. The issues are localized to a couple of patterns that require semantic adjustments beyond pure syntax:
  - `assertRaises` -> `pytest.raises` translation requires adjusting how the caught exception is accessed (`.value` vs `.exception`).
  - TestCase `setUp` or helper-constructed per-test artifacts sometimes are not correctly turned into independent module-level pytest fixtures; the converter sometimes emits placeholder code that must be corrected manually.


Next steps and suggested patches
--------------------------------

Minimal local remediation (safe, low-risk):

1. Fix `pytest.raises` usage in converted tests:

   - Change `cm.exception` -> `cm.value` wherever the converted tests expect the actual exception object.

2. Fix the broken `sql_file` and `schema_file` fixtures in `tests/unit/test_init_api.py`:

   - Implement fixtures that create the files using `create_sql_with_schema` and `temp_dir` fixture, and yield string paths. Example pattern:

       @pytest.fixture
       def sql_file(temp_dir, sql_content):
           sql_file, schema_file = create_sql_with_schema(Path(temp_dir), "test.sql", sql_content)
           yield str(sql_file)

       @pytest.fixture
       def schema_file(temp_dir, sql_content):
           sql_file, schema_file = create_sql_with_schema(Path(temp_dir), "test.sql", sql_content)
           yield str(schema_file)

   - Or rely on class `setUp()` that already creates `self.sql_file`/`self.schema_file` and remove the broken fixtures.

3. Re-run pytest to verify everything is green.

If desired, I can automatically apply these minimal patches and re-run the tests. I will not apply changes unless you ask me to.


Repro steps (what I executed)
-----------------------------

- Activate venv and view help:

  source .venv/Scripts/activate && splurge-unittest-to-pytest --help

- Run converter with backup directory `backups/` (recursive):

  source .venv/Scripts/activate && splurge-unittest-to-pytest -r -b backups/ tests/

- Run pytest in venv:

  source .venv/Scripts/activate && pytest -q


Artifacts in the repo
---------------------

- Converted test files (modified) — see list above.
- Backup files in `backups/` — originals preserved with `.bak` extension.


Closing notes
-------------

The converter produced a mostly-correct translation. Only two failing tests require small semantic fixes. If you want, I can apply the two minimal fixes and re-run the suite to produce a clean, fully-converted test tree. If you prefer to review changes first, use the `.bak` files to inspect originals.

If you want me to proceed with the fixes and a follow-up test run, reply and I'll make the patches and re-run pytest.
