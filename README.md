# Splurge unittest-to-pytest

A Python library and CLI tool for converting unittest-style tests to modern pytest-style tests using libcst.

## Features

- **Complete assertion conversion**: Converts all common unittest assertions to pytest assertions
- **Smart import handling**: Removes unittest imports and adds pytest imports when needed
- **setUp/tearDown conversion**: Converts to pytest fixtures with proper decorators
- **Class inheritance cleanup**: Removes unittest.TestCase inheritance
- **Preserves formatting**: Uses libcst to maintain code style, comments, and whitespace
- **CLI and library API**: Use as a command-line tool or import as a library
- **Dry-run support**: Preview changes before applying them
- **Recursive directory processing**: Find and convert all unittest files in a project

## Installation

```bash
pip install splurge-unittest-to-pytest
```

For development:

```bash
git clone https://github.com/yourusername/splurge-unittest-to-pytest
cd splurge-unittest-to-pytest
pip install -e ".[dev]"
```

## Quick Start

### Command Line

```bash
# Convert a single file
splurge-convert test_example.py

# Convert multiple files
splurge-convert test_*.py

# Convert all unittest files in a directory recursively
splurge-convert --recursive tests/

# Dry run to preview changes
splurge-convert --dry-run --recursive tests/

# Convert to a different directory
splurge-convert --output-dir converted_tests/ test_*.py
```

### Python API

```python
from splurge_unittest_to_pytest import convert_string, convert_file

# Convert code string
unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1 + 1, 2)
        self.assertTrue(True)
"""

result = convert_string(unittest_code)
print(result.converted_code)

# Convert file
result = convert_file("test_example.py", "test_example_pytest.py")
if result.has_changes:
    print("File converted successfully!")
```

## Conversion Examples

### Before (unittest)

```python
import unittest
from unittest.mock import patch

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()
    
    def tearDown(self):
        self.calc.cleanup()
    
    def test_addition(self):
        result = self.calc.add(2, 3)
        self.assertEqual(result, 5)
        self.assertIsInstance(result, int)
    
    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            self.calc.divide(10, 0)
    
    def test_negative_numbers(self):
        self.assertLess(self.calc.add(-1, -1), 0)
        self.assertTrue(self.calc.add(-5, 3) < 0)
```

### After (pytest)

```python
from pytest import *
from unittest.mock import patch

class TestCalculator:
    @pytest.fixture
    def setup_method(self):
        self.calc = Calculator()
    
    @pytest.fixture(autouse=True)
    def teardown_method(self):
        yield
        self.calc.cleanup()
    
    def test_addition(self):
        result = self.calc.add(2, 3)
        assert result == 5
        assert isinstance(result, int)
    
    def test_division_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            pass
    
    def test_negative_numbers(self):
        assert self.calc.add(-1, -1) < 0
        assert self.calc.add(-5, 3) < 0
```

## Supported Conversions

### Assertions

| unittest | pytest |
|----------|--------|
| `self.assertEqual(a, b)` | `assert a == b` |
| `self.assertNotEqual(a, b)` | `assert a != b` |
| `self.assertTrue(x)` | `assert x` |
| `self.assertFalse(x)` | `assert not x` |
| `self.assertIsNone(x)` | `assert x is None` |
| `self.assertIsNotNone(x)` | `assert x is not None` |
| `self.assertIn(a, b)` | `assert a in b` |
| `self.assertNotIn(a, b)` | `assert a not in b` |
| `self.assertIsInstance(a, b)` | `assert isinstance(a, b)` |
| `self.assertNotIsInstance(a, b)` | `assert not isinstance(a, b)` |
| `self.assertGreater(a, b)` | `assert a > b` |
| `self.assertGreaterEqual(a, b)` | `assert a >= b` |
| `self.assertLess(a, b)` | `assert a < b` |
| `self.assertLessEqual(a, b)` | `assert a <= b` |
| `self.assertRaises(Exception)` | `with pytest.raises(Exception):` |
| `self.assertRaisesRegex(Exception, pattern)` | `with pytest.raises(Exception, match=pattern):` |

### Class Structure

- Removes `unittest.TestCase` inheritance
- Converts `setUp()` to `@pytest.fixture` decorated `setup_method()`
- Converts `tearDown()` to `@pytest.fixture(autouse=True)` decorated `teardown_method()` with yield pattern

### Import Management

- Removes `import unittest` and `from unittest import ...` statements
- Adds `from pytest import *` when pytest features are used
- Preserves other imports

## CLI Options

```
Usage: splurge-convert [OPTIONS] [PATHS]...

  Convert unittest-style tests to pytest-style tests.

Options:
  --version                Show the version and exit.
  -o, --output-dir PATH    Output directory for converted files (default: overwrite in place)
  -n, --dry-run           Show what would be converted without making changes
  -r, --recursive         Recursively find unittest files in directories
  --encoding TEXT         Text encoding for reading/writing files (default: utf-8)
  -v, --verbose           Show detailed output
  --help                  Show this message and exit.
```

## Library API

### Core Functions

#### `convert_string(source_code: str) -> ConversionResult`

Convert unittest code string to pytest style.

```python
result = convert_string(unittest_code)
print(f"Converted: {result.has_changes}")
print(f"Errors: {result.errors}")
print(result.converted_code)
```

#### `convert_file(input_path, output_path=None, encoding="utf-8") -> ConversionResult`

Convert a unittest file to pytest style.

```python
# Convert in place
result = convert_file("test_example.py")

# Convert to new file
result = convert_file("test_example.py", "test_example_pytest.py")
```

#### `find_unittest_files(directory: Path) -> list[Path]`

Find all Python files in a directory that appear to contain unittest tests.

```python
from pathlib import Path
unittest_files = find_unittest_files(Path("tests/"))
```

### ConversionResult

```python
@dataclass
class ConversionResult:
    original_code: str      # Original source code
    converted_code: str     # Converted source code  
    has_changes: bool       # Whether any changes were made
    errors: list[str]       # List of any errors encountered
```

## Development

### Setup

```bash
git clone https://github.com/yourusername/splurge-unittest-to-pytest
cd splurge-unittest-to-pytest
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
ruff check src/ tests/
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [libcst](https://libcst.readthedocs.io/) for robust Python code transformation
- Inspired by [unittest2pytest](https://github.com/pytest-dev/unittest2pytest)
- CLI built with [Click](https://click.palletsprojects.com/)
