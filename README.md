# Splurge unittest-to-pytest

[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/splurge-unittest-to-pytest.svg)](https://pypi.org/project/splurge-unittest-to-pytest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

[![Tests](https://img.shields.io/badge/tests-139%20passed-brightgreen.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest)
[![Code Coverage](https://img.shields.io/badge/coverage-82%25-green.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest)
[![Code Quality](https://img.shields.io/badge/code%20quality-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checking](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](https://mypy-lang.org/)

[![Quick checks](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci.yml/badge.svg?query=workflow%3A%22Quick+checks+%28lint%2C+type%2C+tests%29%22)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci.yml)
[![Coverage workflow](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/coverage.yml/badge.svg?query=workflow%3A%22Coverage+%28main+branch+only%29%22)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/coverage.yml)
[![Quick status](https://img.shields.io/github/actions/workflow/status/jim-schilling/splurge-unittest-to-pytest/ci.yml?label=quick&style=flat-square&query=workflow%3A%22Quick+checks+%28lint%2C+type%2C+tests%29%22)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci.yml)
[![Coverage status](https://img.shields.io/github/actions/workflow/status/jim-schilling/splurge-unittest-to-pytest/coverage.yml?label=coverage&style=flat-square)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/coverage.yml)

A small library and CLI tool to convert unittest-style tests into pytest-style tests while preserving formatting and comments using libcst.

Full developer documentation is available in `docs/README-DETAILS.md`.

## Quick Links

- Project: https://github.com/jim-schilling/splurge-unittest-to-pytest
- PyPI: https://pypi.org/project/splurge-unittest-to-pytest/

## Installation

Install from PyPI:

```bash
pip install splurge-unittest-to-pytest
```

For development, clone and install editable dependencies:

```bash
git clone https://github.com/jim-schilling/splurge-unittest-to-pytest
cd splurge-unittest-to-pytest
pip install -e ".[dev]"
```

## Usage

Basic programmatic usage:

```python
from splurge_unittest_to_pytest import convert_string, convert_file

result = convert_string(unittest_source_code)
print(result.converted_code)
```

CLI usage:

```bash
splurge-unittest-to-pytest [OPTIONS] [PATHS]...
```

See `--help` for all CLI options.

## Supported conversions (high level)

- Assertion conversions (a few examples):
  - `self.assertEqual(a, b)` → `assert a == b`
  - `self.assertTrue(x)` → `assert x`
  - `self.assertIsNone(x)` → `assert x is None`
  - `self.assertRaises(Exception)` → `with pytest.raises(Exception):`

- Class and fixture conversions:
  - Remove `unittest.TestCase` inheritance where applicable
  - Convert `setUp`/`tearDown` into pytest fixtures (yield pattern for teardown)

- Import management: remove `unittest` imports and add pytest imports when required

See `docs/README-DETAILS.md` for a complete list of conversions and examples.

## Developer guide

Run tests and checks locally:

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=splurge_unittest_to_pytest --cov-report=term-missing

# Lint and format
ruff check . && ruff format .

# Type check
mypy splurge_unittest_to_pytest/
```

Key developer notes:
- Internal helper utilities live in `splurge_unittest_to_pytest.converter.helpers`.
- The converter uses libcst to perform safe, formatting-preserving transformations.

## Contributing

1. Fork the repository and create a feature branch.
2. Add or update tests in `tests/unit/`.
3. Run the test suite and linters locally.
4. Open a pull request describing the change.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgments

- Built with libcst for robust code transformations.
- Inspired by existing unittest→pytest conversion tools and projects.
# Splurge unittest-to-pytest

[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/splurge-unittest-to-pytest.svg)](https://pypi.org/project/splurge-unittest-to-pytest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

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

# Splurge unittest-to-pytest

A small tool to convert unittest-style tests into pytest-style tests while preserving formatting and comments.

Full documentation, developer guide, and examples are in `docs/README-DETAILS.md`.

Quick start

```bash
pip install splurge-unittest-to-pytest
```

Development

```bash
git clone https://github.com/jim-schilling/splurge-unittest-to-pytest
cd splurge-unittest-to-pytest
pip install -e ".[dev]"
```

API

```python
from splurge_unittest_to_pytest import convert_string, convert_file
```

Notes

- Internal helpers are consolidated in `splurge_unittest_to_pytest.converter.helpers`.
- The detailed documentation and development guide lives in `docs/README-DETAILS.md`.
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


### Internal helpers (note)

A small set of internal helper utilities used by the converter has been
consolidated into a single module: `splurge_unittest_to_pytest.converter.helpers`.
This module is intended for internal reuse across the package. External users
should prefer the public API (`convert_string`, `convert_file`, and the CLI).

If you previously imported helpers from `splurge_unittest_to_pytest.converter.utils`
or `splurge_unittest_to_pytest.converter.core`, update your imports to:

```python
from splurge_unittest_to_pytest.converter.helpers import normalize_method_name
```

Note: `converter.core` has been removed to reduce indirection; importing
internal modules is not part of the stable public API and may change without
notice. See `docs/plan-simplification-2025-09-12.md` for the migration plan and
rationale.
### Performance Improvements

- **Fast execution**: All 47 tests complete in under 60 seconds
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

## Inspecting diagnostics artifacts

When diagnostics are enabled (SPLURGE_ENABLE_DIAGNOSTICS=1) the tool writes a
run-specific diagnostics directory under the system temporary folder by
default. You can override the root location with the environment variable
`SPLURGE_DIAGNOSTICS_ROOT`.

Quick install (development):

```bash
pip install -e .
```

After installing, a small console script is available to inspect the latest
diagnostics run:

```bash
splurge-print-diagnostics
```

Or run the module directly without installing:

```bash
python -m splurge_unittest_to_pytest.print_diagnostics
```
