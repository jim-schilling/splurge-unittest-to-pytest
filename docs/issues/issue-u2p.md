````markdown
# Issue: splurge-unittest-to-pytest conversion problems (u2p)

Summary
-------
This document captures the observed problems when converting a unittest.TestCase-based test module (example: `tests/unit/test_schema_parser.py.bak.1757364222`) to pytest using `splurge-unittest-to-pytest`, the root causes, immediate fixes applied to the converted output, and recommended improvements for the converter.

Checklist
---------
- [x] Reproduce conversion of the backup file to `tmp/` using the installed converter
- [x] Run pytest on converted output and capture collection/runtime errors
- [x] Identify root causes and list minimal, safe fixes for converted files
- [ ] Implement converter code changes (recommended follow-ups)

Observed symptoms
-----------------
- Collection-time failures (NameError: `pytest` is not defined) because the converter placed `@pytest.fixture()` decorators before `import pytest`.
- Fixtures that produced incorrect values or performed cleanup on the wrong symbol (for example, calling `shutil.rmtree(temp_dir, ...)` where `temp_dir` was the fixture function, not the created path).
- Tests left as instance-methods expecting `self.<attr>` (from `unittest.TestCase`) while the converter emitted function-style tests using fixtures, producing AttributeError when methods reference `self.parser` or `self.temp_dir`.
- Converter attempted to read non-text/binary files (e.g., files in `__pycache__`), causing UnicodeDecodeError in some runs.
- Minor logic/variable-name regressions introduced during mechanical translation (e.g., inconsistent use of `tables` vs `tables3` inside tests).

Root causes
-----------
1. Import ordering: top-level imports required by fixtures were missing or placed after fixture declarations.
2. Incorrect fixture bodies: fixtures either failed to `return`/`yield` proper resources or used the fixture function name in cleanup code instead of the produced value.
3. Semantic gap between unittest instance-methods and pytest function-style tests: converter did not attach fixture-provided values to test class instances.
4. File scanning: converter didn't reliably ignore binary files or `__pycache__` directories when scanning for files to convert.

Immediate, minimal fixes applied to converted output
-------------------------------------------------
These are the safe edits used to make the converted file runnable. They are meant to be short-term compatibility fixes that another agent can apply to converter output.

1) Ensure imports appear before fixtures

Move these imports to the top of the converted file (before any `@pytest.fixture()`):

```python
import pytest
import os
import shutil
import tempfile
from splurge_sql_generator.schema_parser import SchemaParser
```

2) Fix `temp_dir` fixture pattern

Historical note
---------------
The legacy compatibility mode and engine selection options (for example, the historical compatibility flag and engine=) were removed in release 2025.1.0. This issue writeup is retained for historical context and documents behaviors observed prior to that change.
@pytest.fixture()
def temp_dir():
    tmpdir = tempfile.mkdtemp()

3) Ensure `parser` fixture returns instance

```python
@pytest.fixture()
def parser():
    return SchemaParser()
```

4) Add autouse compatibility glue for unittest.TestCase methods

If converted output still contains class-based test methods expecting `self.<attr>`, add this small autouse fixture to attach fixtures to the test instance:

    ```python
    @pytest.fixture(autouse=True)
    def _attach_to_instance(request, parser, temp_dir):
        inst = getattr(request, "instance", None)
        if inst is not None:
            setattr(inst, "parser", parser)
            setattr(inst, "temp_dir", temp_dir)
    ```

This keeps behavioral compatibility and avoids rewriting all methods to accept fixtures.

5) Fix variable-name errors introduced during conversion

Scan for obvious mismatches (e.g., `schema = tables["mytable"]` vs `tables3` usage) and correct them to use the variable holding parsed results.

Reproduction steps
------------------
1. Convert the backup file to `tmp/`:

```bash
splurge-unittest-to-pytest --output tmp tests/unit/test_schema_parser.py.bak.1757364222 --verbose
```

2. Copy to a `.py` name so pytest will collect it (optional if converter wrote .py already):

```bash
cp tmp/test_schema_parser.py.bak.1757364222 tmp/test_schema_parser_converted.py
```

3. Run pytest on the converted file and inspect the first failures:

```bash
python -m pytest -q tmp/test_schema_parser_converted.py
```

Typical first failure: `NameError: name 'pytest' is not defined` during collection — fix import ordering as shown above.

Why these fixes are safe
-----------------------
- Reordering imports only affects module initialization and resolves decorators evaluated at import time.
- Yielding and cleaning the actual temporary path prevents cleanup from receiving the wrong object type.
- Attaching fixtures to `request.instance` is limited to tests executed as class methods and is opt-in by presence of `request.instance`; it's non-invasive for pure function-style tests.

Converter improvement recommendations (follow-ups)
-------------------------------------------------
- Skip binary files and `__pycache__` during file discovery; detect and ignore non-UTF8 files gracefully and log a warning.
- Ensure generated fixtures always `return` or `yield` values that tests expect; add template patterns for common fixture types (tempdir, tmp_path, db connection, etc.).
- Add an optional legacy compatibility flag that emits the autouse attachment glue when converting `unittest.TestCase` classes to pytest to avoid manual edits.
- Add unit tests for the converter that cover:
  - fixtures-before-imports scenario
  - tempdir fixture rewrite correctness
  - class-methods compatibility via autouse fixture
  - ignoring non-text files

Validation checklist
--------------------
After applying the edits to converted output, run these steps and expect no collection errors and successful test execution (or actionable test failures originating from logic rather than conversion):

```bash
python -m pytest -q tmp/test_schema_parser_converted.py
```

If pytest still errors, open the first traceback and fix the corresponding fixture or variable name referenced in the stack trace.

Notes / context
---------------
- The authoritative original file used for conversion is `tests/unit/test_schema_parser.py.bak.1757364222` (class-based `unittest.TestCase`). The converter created `tmp/test_schema_parser.py.bak.1757364222` which required the immediate fixes above to be runnable under pytest.
- These changes were intentionally minimal to preserve test semantics while proving that converter output can be made runnable with small, repeatable edits.

Contact / next steps
-------------------
If you want, I can either:

- Produce an automated patch that applies the minimal edits to a converted file in `tmp/` (recommended for quick validation). OR
- Implement the converter improvements (ignore `__pycache__`, reorder imports, generate compatibility glue) as code changes in the `splurge-unittest-to-pytest` project and add tests for the converter.

Select which follow-up you want and I will implement it.

Recent runs & evidence
----------------------
- Command run (converter help):

    ```bash
    splurge-unittest-to-pytest --help
    ```

    Observed legacy compatibility flag exists (historical behavior) that was supposed to emit an autouse fixture to attach fixtures to `unittest.TestCase` instances.

- Conversion run used for this investigation:

    ```bash
    splurge-unittest-to-pytest --output tmp --backup backups tests/unit/test_schema_parser.py.bak.1757364222 --verbose
    ```

    Output: backup created `backups/test_schema_parser.py.bak.1757364222.bak`, converted file written to `tmp/test_schema_parser.py.bak.1757364222`.

- Pytest run on the converted file initially produced collection-time errors:

    - `NameError: name 'pytest' is not defined` during collection. This showed that the converter still emitted `@pytest.fixture()` decorators before placing `import pytest` at the top of the module.

Local quick-fix applied (for validation)
--------------------------------------
To validate the minimal edits required to make the converted output runnable, the following short fixes were applied to `tmp/test_schema_parser.py.bak.1757364222` (local, not pushed):

- Move `import pytest` and other imports (`os`, `shutil`, `tempfile`, and `SchemaParser` import) to the top of the file before any `@pytest.fixture()` usage.
- Replace `temp_dir` fixture with a yield/cleanup pattern using a local `tmpdir` variable and cleaning that variable in `finally`.
- Ensure `parser` fixture returns `SchemaParser()`.
- Change the autouse fixture to accept `parser` and `temp_dir` and attach those concrete values to `request.instance`.

After these local edits, pytest was able to collect the converted file (collection errors removed). These edits represent the minimal, safe hygiene changes needed on the converted file itself.

Requirements coverage (mapping)
-----------------------------
- Fix imports before fixtures: Done (documents steps and example patch)
- Fix temp_dir fixture yield/cleanup pattern: Done (documented and applied locally)
- Ensure parser fixture returns instance: Done (documented and applied locally)
- Autouse glue to attach fixtures to instances: Partially done — converter already has `--compat`, but it emitted the glue before imports; requirement is to ensure the glue generation happens after imports and uses the produced fixture values (documented as recommended change)
- Ignore non-UTF8/binary files: Not implemented — recommended change for the converter

Status summary
--------------
- Converter: new version installed and nominally supports `--compat` but still produces import-order issues causing collection-time NameError.
- Repo-level test file `tests/unit/test_schema_parser.py.bak.1757364222` used as canonical input. Converted output written to `tmp/` and backed up.
- Short-term fix: local edits to `tmp/` file make the converted file runnable. Long-term fix: update the converter to emit imports at top, produce correct fixtures, and ensure compat glue references real fixture values.

```