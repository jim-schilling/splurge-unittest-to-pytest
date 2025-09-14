## Conversion run: splurge-unittest-to-pytest (u2p run: 2025-09-14-f)

Date: 2025-09-14

Summary
-------
- Action: Reverted tests to HEAD, ran `splurge-unittest-to-pytest -r -b backups/u2p-2025-09-14-f tests/`, then executed `pytest -q`.
- Backups: `backups/u2p-2025-09-14-f/` (original files saved as `.bak`).
- Outcome: 113 passed, 3 failed.

Failing tests (short)
--------------------
1) tests/unit/test_schema_parser_edge_cases.py::test_parse_schema_file_sql_validation_error_propagates
   - Error: AttributeError: 'ExceptionInfo' object has no attribute 'exception'

2) tests/unit/test_schema_parser.py::test_load_schema_missing_file
   - Error: AttributeError: 'ExceptionInfo' object has no attribute 'exception'

3) tests/unit/test_parameter_validation.py::test_invalid_parameters_raise_error
   - Error: AttributeError: 'ExceptionInfo' object has no attribute 'exception'

Observed pytest output (key patterns)
------------------------------------
- The failing assertions use a pytest pattern like:

```python
with pytest.raises(SomeError) as cm:
    func()
assert 'expected message' in str(cm.exception)
```

- In pytest, the context manager variable `cm` is an ExceptionInfo object and the original exception is available as `cm.value` (not `cm.exception`). Accessing `cm.exception` raises AttributeError.

Root cause analysis
-------------------
- The test converter correctly converted exception-assertions to `with pytest.raises(...) as cm:`, but it left downstream code using the unittest idiom `cm.exception` (unittest's `assertRaises` returns a context where `.exception` holds the exception). Pytest's ExceptionInfo uses `.value`. This is a semantic mismatch introduced by the conversion.

Minimal fixes
-------------
1) Replace uses of `cm.exception` with `cm.value` or `str(cm.value)` depending on how the exception message is inspected. Examples:

```python
with pytest.raises(SqlValidationError) as cm:
    parser.parse_schema_file(path)
assert 'SQL validation error in schema file' in str(cm.value)
```

2) Optionally run a small search/replace across converted tests:

```text
find: cm.exception
replace: cm.value
```

3) Review any tests that expect `.exception` attributes of the older unittest context and convert them to refer to `.value` or use `match=` parameter on pytest.raises for simple substring assertions:

```python
with pytest.raises(SqlValidationError, match='SQL validation error in schema file'):
    parser.parse_schema_file(path)
```

Impact and risk
---------------
- This is a low-risk, mechanical transformation. Replacing `cm.exception` with `cm.value` is safe for tests that only inspect the exception message or type. Using `match=` with pytest.raises is even simpler and more idiomatic.

Next steps
----------
- If you'd like, I can:
  1. Apply a conservative patch replacing `cm.exception` → `cm.value` across the converted tests (only where `cm.exception` is referenced),
  2. Re-run pytest and iterate on any remaining issues.

Please confirm if you want me to proceed with the automatic fix (I will open a PR-style diff here and run the tests). If you prefer to review changes first, I can produce a patch file for review instead.
