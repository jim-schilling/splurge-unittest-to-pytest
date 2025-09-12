Why some test data contain intentionally-bad Python

Some files under `tests/data/` include examples of malformed or poor-quality
Python on purpose (for example, `assert 1 is not None`). These examples are
used to exercise the converter's behavior when given user code that may be
syntactically valid but semantically questionable.

Why we keep them:
- They reproduce real-world mistakes that users may have in legacy code.
- They ensure the converter preserves or signals questionable constructs
  consistently (we prefer to leave decisions to the user rather than silently
  'fixing' their code).

Notes for test runners and maintainers:
- Some of these example files produce `SyntaxWarning` about `is not` with
  literal values when executed under CPython. Tests that generate temporary
  converted files filter these warnings during test runs. If you want to see
  the warnings locally, remove the filter in `tests/conftest.py`.
- If you intend to make the converter change these cases automatically, be
  aware that altering the conversion may break the intent of these tests.
