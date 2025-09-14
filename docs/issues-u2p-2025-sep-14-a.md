## Issue: unittest->pytest conversion report (u2p run: 2025-09-14)

Date: 2025-09-14

Summary
-------
- Action: Converted the test suite in-place using `splurge-unittest-to-pytest` (backups created under `backups/u2p-2025-09-14-a`) and ran `pytest -q`.
- Outcome: 71 passed, 1 failed (pytests stopped after first failure due to xdist interruption).

Failing test
------------
- Test: `tests/unit/test_init_api.py::test_generate_class`
- Error: FileNotFoundError: File not found: test.sql
- Location (key stack):
  - tests/unit/test_init_api.py:51 -> test_generate_class called `generate_class(sql_file, schema_file_path=schema_file)`
  - generate_class -> code_generator.generate_class -> parser.parse_file
  - sql_parser.parse_file -> safe_read_file(file_path) -> FileNotFoundError('test.sql')

Reproduction
------------
Run in the project venv from the repository root:

```bash
source .venv/Scripts/activate
pytest -q
```

Observed behavior
-----------------
- The converted pytest test invoked `generate_class` with `sql_file` and `schema_file` values of `'test.sql'` (strings). The parser attempted to open `'test.sql'` relative to the current working directory, but that file did not exist, raising FileNotFoundError.
- The rest of the converted suite ran correctly: 71 tests passed.

Root cause analysis
-------------------
1. The original unittest version used `setUp` to create a temporary directory and created real files (via `create_sql_with_schema(Path(self.temp_dir), 'test.sql', self.sql_content)`), storing full paths in `self.sql_file` and `self.schema_file`.
2. The converted pytest version contains fixtures that return bare filenames (e.g. `return 'test.sql'`) rather than absolute paths pointing to files created in the temporary directory. The conversion produced a fixture `init_api_data()` that calls `create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)` but that fixture is not wired to the `test_generate_class` usage; instead, the test uses `sql_file` and `schema_file` fixtures which return mere strings.
3. Because `generate_class` expects real file paths (the parser calls `safe_read_file`), passing a bare filename that wasn't created in the current working directory results in FileNotFoundError.

Expected behavior
-----------------
- The test should create the temporary SQL file and pass its actual path to `generate_class`. After conversion to pytest, the fixtures should either:
  - create the file in the temp dir and return an absolute path (preferred), or
  - the test should join `temp_dir` with the filename before calling `generate_class`.

Recommended minimal fix
---------------------
- Fix the `sql_file` and `schema_file` fixtures to return an absolute path into `temp_dir` where the helper `create_sql_with_schema` wrote the files. Example (pseudo):

```python
@pytest.fixture
def sql_file(temp_dir, sql_content):
    path = Path(temp_dir) / 'test.sql'
    path.write_text(sql_content)
    return str(path)

@pytest.fixture
def schema_file(temp_dir, sql_content):
    path = Path(temp_dir) / 'test.sql'
    # if schema content differs, write schema content; otherwise reuse
    return str(path)
```

- Alternatively, modify `test_generate_class` to compute full paths before calling `generate_class`:

```python
sql_path = os.path.join(temp_dir, sql_file)
schema_path = os.path.join(temp_dir, schema_file)
code = generate_class(sql_path, schema_file_path=schema_path)
```

Both approaches ensure `generate_class` receives a filesystem path that `safe_read_file` can open.

Next steps
----------
- If you want, I can apply the fixture-based patch to `tests/unit/test_init_api.py` (and any similarly-affected tests), then re-run pytest and report back. This is a small, low-risk change that should turn the single failing test green.

Attachments: original unittest and converted pytest code for `tests/unit/test_init_api.py` follow.

==UNITTEST==

```python
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from splurge_sql_generator import generate_class, generate_multiple_classes
from tests.unit.test_utils import create_sql_with_schema

class TestInitAPI(unittest.TestCase):
    def setUp(self):
        # Create temporary directory for this test
        self.temp_dir = tempfile.mkdtemp()
        self.sql_content = """# TestClass\n# test_method\nSELECT 1;"""
        
        # Use the shared helper function
        sql_file, schema_file = create_sql_with_schema(
            Path(self.temp_dir), 
            "test.sql", 
            self.sql_content
        )
        self.sql_file = str(sql_file)
        self.schema_file = str(schema_file)

    def tearDown(self):
        # Clean up the entire temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_class(self):
        code = generate_class(self.sql_file, schema_file_path=self.schema_file)
        self.assertIn('class TestClass', code)
        # Test output file
        self.output_file = self.sql_file + '.py'
        generate_class(self.sql_file, output_file_path=self.output_file, schema_file_path=self.schema_file)
        self.assertTrue(os.path.exists(self.output_file))
        with open(self.output_file) as f:
            self.assertIn('class TestClass', f.read())

    def test_generate_multiple_classes(self):
        self.output_dir = self.sql_file + '_outdir'
        os.mkdir(self.output_dir)
        result = generate_multiple_classes([self.sql_file], output_dir=self.output_dir, schema_file_path=self.schema_file)
        self.assertIn('TestClass', result)
        out_file = os.path.join(self.output_dir, 'test_class.py')
        self.assertTrue(os.path.exists(out_file))
        with open(out_file) as f:
            self.assertIn('class TestClass', f.read())

if __name__ == '__main__':
    unittest.main()
```

==PYTEST==

```python
import os
import shutil
import tempfile
from pathlib import Path
from tests.unit.test_utils import create_sql_with_schema
from typing import Any, Generator, NamedTuple

import pytest

from splurge_sql_generator import generate_class, generate_multiple_classes


class _InitAPIData(NamedTuple):
    """Container for test data and resources."""
    sql_file: Any
    schema_file: Any


@pytest.fixture
def init_api_data():
    (sql_file, schema_file) = create_sql_with_schema(
        Path(temp_dir), 
        "test.sql", 
        sql_content
    )
    yield _InitAPIData(sql_file, schema_file)


@pytest.fixture
def temp_dir():
    _temp_dir_value = tempfile.mkdtemp()
    yield _temp_dir_value
    # Clean up the entire temp directory
    shutil.rmtree(_temp_dir_value, ignore_errors=True)


@pytest.fixture
def sql_content():
    return """# TestClass\n# test_method\nSELECT 1;"""


@pytest.fixture
def sql_file():
    return "test.sql"


@pytest.fixture
def schema_file():
    return "test.sql"
def test_generate_class(temp_dir, sql_content, sql_file, schema_file):
    code = generate_class(sql_file, schema_file_path=schema_file)
    assert 'class TestClass' in code
    # Test output file
    output_file = sql_file + '.py'
    generate_class(sql_file, output_file_path=output_file, schema_file_path=schema_file)
    assert os.path.exists(output_file)
    with open(output_file) as f:
        assert 'class TestClass' in f.read()
def test_generate_multiple_classes(temp_dir, sql_content, sql_file, schema_file):
    output_dir = sql_file + '_outdir'
    os.mkdir(output_dir)
    result = generate_multiple_classes([sql_file], output_dir=output_dir, schema_file_path=schema_file)
    assert 'TestClass' in result
    out_file = os.path.join(output_dir, 'test_class.py')
    assert os.path.exists(out_file)
    with open(out_file) as f:
        assert 'class TestClass' in f.read()
```
