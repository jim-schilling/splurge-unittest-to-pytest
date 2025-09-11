# Splurge unittest-to-pytest

[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/splurge-unittest-to-pytest.svg)](https://pypi.org/project/splurge-unittest-to-pytest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![Tests](https://img.shields.io/badge/tests-139%20passed-brightgreen.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest)
[![Code Coverage](https://img.shields.io/badge/coverage-82%25-green.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest)
[![Code Quality](https://img.shields.io/badge/code%20quality-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checking](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](https://mypy-lang.org/)

[![Quick checks](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci.yml/badge.svg?query=workflow%3A%22Quick+checks+%28lint%2C+type%2C+tests%29%22)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci.yml)
[![Coverage](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci.yml/badge.svg?query=workflow%3A%22Coverage+%28main+branch+only%29%22)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci.yml)
[![Quick status](https://img.shields.io/github/actions/workflow/status/jim-schilling/splurge-unittest-to-pytest/ci.yml?label=quick&style=flat-square&query=workflow%3A%22Quick+checks+%28lint%2C+type%2C+tests%29%22)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci.yml)
[![Coverage status](https://img.shields.io/github/actions/workflow/status/jim-schilling/splurge-unittest-to-pytest/coverage.yml?label=coverage&style=flat-square)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/coverage.yml)

A Python library and CLI tool for converting unittest-style tests to modern pytest-style tests using libcst.

## ✨ Features

- **Complete assertion conversion**: Converts all common unittest assertions to pytest assertions
- **Smart import handling**: Removes unittest imports and adds pytest imports when needed
- **setUp/tearDown conversion**: Converts to pytest fixtures with proper decorators
- **Class inheritance cleanup**: Removes unittest.TestCase inheritance
- **Custom method patterns**: Configurable patterns for setup, teardown, and test methods
- **CamelCase/Snake_case support**: Intelligent pattern matching across naming conventions
- **Preserves formatting**: Uses libcst to maintain code style, comments, and whitespace
- **CLI and library API**: Use as a command-line tool or import as a library
- **Dry-run support**: Preview changes before applying them
- **Recursive directory processing**: Find and convert all unittest files in a project
- **Modern development tooling**: Uses ruff for unified linting and formatting
- **Enhanced test infrastructure**: pytest-mock integration and modern test patterns

## 🚀 Installation

```bash
pip install splurge-unittest-to-pytest
```

For development:

```bash
git clone https://github.com/jim-schilling/splurge-unittest-to-pytest
cd splurge-unittest-to-pytest
pip install -e ".[dev]"
```

## 🏃 Quick Start

### Command Line

```bash
# Convert a single file
splurge-unittest-to-pytest test_example.py

# Convert multiple files
splurge-unittest-to-pytest test_*.py

# Convert all unittest files in a directory recursively
splurge-unittest-to-pytest --recursive tests/

# Dry run to preview changes
splurge-unittest-to-pytest --dry-run --recursive tests/

# Convert to a different directory
splurge-unittest-to-pytest --output-dir converted_tests/ test_*.py

# Use custom method patterns (comma-separated)
splurge-unittest-to-pytest --setup-methods "setUp,beforeAll,setup_class" test.py

# Use custom method patterns (multiple flags)
splurge-unittest-to-pytest --setup-methods setUp --setup-methods beforeAll test.py

# Configure all method types
splurge-unittest-to-pytest --setup-methods "setUp,beforeAll" \
                --teardown-methods "tearDown,afterAll" \
                --test-methods "test_,it_,spec_" test.py
```

#### Compatibility and discovery options

- `--compat/--no-compat` (default: `--compat`) — When enabled, the converter emits a small autouse fixture (`_attach_to_instance`) that attaches generated fixtures to `request.instance`, preserving `self.<attr>` access in converted class-based tests. Disable with `--no-compat` if you prefer explicit fixture-only conversions.
Note: The project now uses the staged pipeline as the authoritative conversion engine. The legacy
`UnittestToPytestTransformer` implementation has been archived and moved out of the package proper
to `contrib/legacy_converter.py`. Use the `pipeline` engine via the `convert_string(..., engine='pipeline')`
API or the CLI (default). If you need the legacy transformer for reference, you can import it from
`contrib.legacy_converter` (archived, deprecated).
- Discovery robustness — the converter will skip `__pycache__` directories and gracefully ignore unreadable or binary files during recursive discovery to avoid UnicodeDecodeError or permission errors when scanning large projects.

- Backups — Use `--backup <dir>` to create a copy of each file before it is modified. Backups are saved as `<filename>.bak` in the provided directory. Backups are not created during `--dry-run`.


### Python API

```python
from splurge_unittest_to_pytest import convert_string, convert_file

# Convert code string with default patterns
unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1 + 1, 2)
        self.assertTrue(True)
"""

result = convert_string(unittest_code)
print(result.converted_code)

# Convert with custom method patterns
result = convert_string(
    unittest_code,
    setup_patterns=["setUp", "beforeAll"],
    teardown_patterns=["tearDown", "afterAll"],
    test_patterns=["test_", "it_"]
)

# Convert file
result = convert_file("test_example.py", "test_example_pytest.py")
if result.has_changes:
    print("File converted successfully!")

# Convert file with custom patterns
result = convert_file(
    "test_example.py", 
    "test_example_pytest.py",
    setup_patterns=["setUp", "beforeAll"],
    teardown_patterns=["tearDown", "afterAll"],
    test_patterns=["test_", "it_"]
)
```

## Custom Method Patterns

Splurge supports configurable method name patterns for different testing frameworks and custom conventions. You can specify custom patterns for setup, teardown, and test methods.

### Default Patterns

By default, the converter recognizes these patterns:

- **Setup methods**: `setUp`, `set_up`, `setup`, `setup_method`, `setUp_method`, `before_each`, `beforeEach`, `before_test`, `beforeTest`
- **Teardown methods**: `tearDown`, `tear_down`, `teardown`, `teardown_method`, `tearDown_method`, `after_each`, `afterEach`, `after_test`, `afterTest`
- **Test methods**: `test_`, `test`, `should_`, `when_`, `given_`, `it_`, `spec_`

### Custom Patterns

Use the CLI options to specify custom method patterns:

```bash
# Custom setup patterns for different frameworks
splurge-unittest-to-pytest --setup-methods "beforeEach,beforeAll,setup_class" test.js

# Custom test patterns for BDD-style tests
splurge-unittest-to-pytest --test-methods "describe_,it_,context_" test.js

# Mix and match patterns
splurge-unittest-to-pytest --setup-methods "setUp,beforeAll" \
                --teardown-methods "tearDown,afterAll" \
                --test-methods "test_,should_,it_" test.py
```

### Pattern Matching Features

- **Case-insensitive**: `setUp` matches `setup`, `SETUP`, etc.
- **CamelCase/Snake_case**: `beforeAll` matches `before_all` and vice versa
- **Multiple patterns**: Separate with commas or use multiple flags
- **Flexible syntax**: Supports both `pattern_` (prefix) and `pattern` (exact) matching

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
import pytest

@pytest.fixture
def calc():
    calculator = Calculator()
    yield calculator
    calculator.cleanup()

def test_addition(calc):
    result = calc.add(2, 3)
    assert result == 5
    assert isinstance(result, int)

def test_division_by_zero(calc):
    with pytest.raises(ZeroDivisionError):
        calc.divide(10, 0)

def test_negative_numbers(calc):
    assert calc.add(-1, -1) < 0
    assert calc.add(-5, 3) < 0
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

## Note on assertIsNone / assertIsNotNone with literals

The converter transforms `self.assertIsNone(x)` into `assert x is None` and
`self.assertIsNotNone(x)` into `assert x is not None`. If `x` is a literal
value (for example an integer or string literal), Python may emit a
SyntaxWarning like "is not with a literal" when running the converted code.
This is a known limitation of performing the idiomatic `is`/`is not` conversion
for literal operands; the conversion intentionally uses `is`/`is not` to match
the semantic intent for `None` checks. If you prefer to avoid these warnings
you can edit the converted assertions to use `== None` / `!= None` instead.


## CLI Options

```
Usage: splurge-unittest-to-pytest [OPTIONS] [PATHS]...

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

## Modern Test Infrastructure

Version 2025.0.0 introduces significant improvements to the test infrastructure:

### Enhanced Testing Features

- **pytest-mock integration**: Modern mocking with `mocker` fixture instead of `unittest.mock`
- **tmp_path fixtures**: Proper temporary file handling with pytest's `tmp_path` fixture
- **Parallel test execution**: Support for running tests in parallel with `pytest-xdist`
- **Comprehensive coverage**: 85%+ code coverage with detailed reporting
- **Unified tooling**: Single tool (ruff) for linting, formatting, and security validation

### Performance Improvements

- **Fast execution**: All 47 tests complete in under 60 seconds
- **Memory efficient**: Uses streaming for large file processing
- **Reliable conversions**: Comprehensive test suite validates all conversion scenarios
- **Type safety**: Full mypy type checking for better code quality

### Development Workflow

```bash
# Run tests with coverage and parallel execution
pytest -n auto --cov=splurge_unittest_to_pytest --cov-report=term-missing

# Lint and format in one command
ruff check . && ruff format .

# Type check
mypy splurge_unittest_to_pytest/
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
git clone https://github.com/jim-schilling/splurge-unittest-to-pytest
cd splurge-unittest-to-pytest
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=splurge_unittest_to_pytest --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_converter.py

# Run tests in parallel
pytest -n auto
```

### Code Quality

```bash
# Format code
ruff format .

# Lint and check
ruff check .

# Type check
mypy splurge_unittest_to_pytest/
```

### Development Tools

- **pytest**: Testing framework with modern fixtures and plugins
- **pytest-mock**: Enhanced mocking capabilities for pytest
- **pytest-cov**: Code coverage reporting
- **ruff**: Unified linting, formatting, and security validation
- **mypy**: Static type checking
- **libcst**: AST-based code transformation library

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
- Modern testing infrastructure powered by [pytest](https://pytest.org/) and [pytest-mock](https://pytest-mock.readthedocs.io/)
- Code quality maintained with [ruff](https://beta.ruff.rs/docs/)
