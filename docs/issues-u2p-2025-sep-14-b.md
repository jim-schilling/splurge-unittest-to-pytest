## Conversion run: splurge-unittest-to-pytest (u2p run: 2025-09-14-b)

Date: 2025-09-14

Summary
-------
- Action: Reverted tests to HEAD, re-ran `splurge-unittest-to-pytest -r -b backups/u2p-2025-09-14-b tests/`, then executed `pytest -q`.
- Outcome: 110 passed, 2 failed, 1 error (xdist stopped after multiple failures). Backups stored in `backups/u2p-2025-09-14-b`.

Failing items
-------------
1) AttributeError: 'ExceptionInfo' object has no attribute 'exception'
   - Tests affected:
     - tests/unit/test_schema_parser_edge_cases.py::test_parse_schema_file_sql_validation_error_propagates
     - tests/unit/test_schema_parser.py::test_load_schema_missing_file
   - Root cause: converter transformed unittest-style exception assertions that accessed the exception via the unittest API (e.g., `cm.exception`) into pytest's `with pytest.raises(...) as cm:` pattern but left the code using `cm.exception`. In pytest `cm` is an ExceptionInfo object and the raised exception is available via `cm.value` (or str(cm.value)). Using `cm.exception` causes AttributeError.

2) TypeError when calling `Path(temp_dir)` inside fixture
   - Test affected: tests/unit/test_init_api.py::test_generate_class (error happens in fixture `init_api_data` during setup)
   - Root cause: the converter produced an `init_api_data` fixture that calls `create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)` but used `temp_dir` as a fixture reference rather than a value. In other words, it attempted to call `Path(temp_dir)` where `temp_dir` is a pytest fixture object, not the resolved string/path value. This indicates the converter generated code that references other fixtures by name inside a fixture body without accepting them as function parameters. The correct pattern is to declare dependencies as function parameters: `def init_api_data(temp_dir, sql_content):` and then use `Path(temp_dir)`.

Observed behavior
-----------------
- Three distinct issues stopped the run: two occurrences of the ExceptionInfo attribute bug, and one TypeError from incorrect fixture parameter usage. Many other tests passed (110), so conversion is largely successful but these semantic issues require small, targeted edits.

Fix recommendations
-------------------
1) Replace `cm.exception` with `cm.value` (or `str(cm.value)`) in tests converted to `with pytest.raises(...) as cm:`. Example:

```python
with pytest.raises(SomeError) as cm:
    do_something()
assert 'expected message' in str(cm.value)
```

2) Fix fixtures that reference other fixtures by name without declaring them as parameters. For example, change:

```python
@pytest.fixture
def init_api_data():
    (sql_file, schema_file) = create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)
    ...
```

to:

```python
@pytest.fixture
def init_api_data(temp_dir, sql_content):
    (sql_file, schema_file) = create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)
    ...
```

3) Ensure fixtures that return filenames return full paths to the files created in the temp directory (see previous report `issues-u2p-2025-sep-14-a.md`). For example:

```python
@pytest.fixture
def sql_file(temp_dir, sql_content):
    p = Path(temp_dir) / 'test.sql'
    p.write_text(sql_content, encoding='utf-8')
    return str(p)
```

Planned next steps
------------------
- If you authorize, I can apply the minimal, low-risk changes:
  1. Replace `cm.exception` uses with `cm.value` or `str(cm.value)` across converted tests.
  2. Fix any fixture definitions that reference other fixtures without declaring them as parameters.
  3. Ensure file-returning fixtures write files into `temp_dir` and return absolute paths.
  4. Re-run pytest until green or until remaining issues are identified.

These fixes are conservative, small, and target only the converted tests. Let me know if you'd like me to proceed and I'll implement them, run the test suite, and commit/diff the changes.
