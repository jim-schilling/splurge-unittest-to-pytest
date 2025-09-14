## Conversion run: splurge-unittest-to-pytest (u2p run: 2025-09-14-d)

Date: 2025-09-14

Summary
-------
- Action: Reverted tests to HEAD, ran `splurge-unittest-to-pytest -r -b backups/u2p-2025-09-14-d tests/`, then executed `pytest -q`.
- Outcome: 71 passed, 1 error. Backups are in `backups/u2p-2025-09-14-d`.

Error detail
------------
- Error: TypeError during fixture setup in `tests/unit/test_init_api.py::test_generate_class`.
- Pytest output (key lines):

  ERROR at setup of test_generate_class
  tests/unit/test_init_api.py:22
  TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'FixtureFunctionDefinition'

Diagnosis
---------
- The converted `init_api_data` fixture calls `create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)` but `temp_dir` is not declared as a parameter to the fixture. Pytest provides fixture values by injecting them as function parameters; referencing `temp_dir` by name inside the fixture body refers to the fixture object definition, not its resolved value. Passing that fixture object into `Path()` causes the TypeError.

Minimal fix
---------
- Change the fixture signature to accept `temp_dir` and `sql_content` (or other dependent fixtures) as parameters so pytest injects their resolved values:

```python
@pytest.fixture
def init_api_data(temp_dir, sql_content):
    sql_file, schema_file = create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)
    yield (sql_file, schema_file)
```

- Also ensure fixtures that return filenames return full paths created inside `temp_dir` (example):

```python
@pytest.fixture
def sql_file(temp_dir, sql_content):
    p = Path(temp_dir) / 'test.sql'
    p.write_text(sql_content, encoding='utf-8')
    return str(p)
```

Why this works
--------------
- Pytest resolves fixtures by calling the fixture function and injecting resolved fixture values as function parameters. Declaring dependencies in the function signature ensures `temp_dir` is the actual temporary directory path (string) and not the fixture object reference.

Next steps
----------
- I can apply these minimal, targeted edits to the affected test(s) and re-run pytest. This is low-risk and should fix the current error. If you want me to proceed, I'll:
  1. Edit `tests/unit/test_init_api.py` to accept `temp_dir` and `sql_content` in the `init_api_data` fixture and ensure returned file paths are absolute and created inside `temp_dir`.
  2. Re-run pytest and report results.

Backups and artifacts
---------------------
- Converted tests (in-place): `tests/` (converted files list saved by the converter).
- Backups: `backups/u2p-2025-09-14-d/` (contains `.bak` originals for converted files).

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
def sql_file(init_api_data):
  return init_api_data.sql_file


@pytest.fixture
def schema_file(init_api_data):
  return init_api_data.schema_file
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
