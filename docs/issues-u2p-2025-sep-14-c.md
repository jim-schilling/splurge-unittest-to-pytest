## Conversion run: splurge-unittest-to-pytest (u2p run: 2025-09-14-c)

Date: 2025-09-14

Summary
-------
- Action: Reverted tests to HEAD, re-ran converter with backups to `backups/u2p-2025-09-14-c`, then executed `pytest -q`.
- Outcome: 71 passed, 1 error. Backups are under `backups/u2p-2025-09-14-c`.

Error detail
------------
- Error: TypeError in setup of `tests/unit/test_init_api.py::test_generate_class`.
- Trace: the fixture `init_api_data` calls `create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)` but `temp_dir` was referenced as a fixture object rather than declared as a function parameter. This results in `Path` being passed a `FixtureFunctionDefinition` rather than a string/path and raises TypeError.

Fix recommendation
------------------
- Modify the fixture to accept `temp_dir` and `sql_content` as parameters, for example:

```python
@pytest.fixture
def init_api_data(temp_dir, sql_content):
    sql_file, schema_file = create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)
    yield (sql_file, schema_file)
```

This change aligns with pytest's fixture dependency injection and ensures `temp_dir` resolves to the temporary directory path before use.

Next steps
----------
- If you'd like, I can apply this targeted fixture-fix and re-run pytest to confirm green. It's a small edit and low-risk.
