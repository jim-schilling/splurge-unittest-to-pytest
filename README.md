# Splurge unittest-to-pytest

[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/splurge-unittest-to-pytest.svg)](https://pypi.org/project/splurge-unittest-to-pytest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

[![Tests](https://img.shields.io/badge/tests-1096%20passed-brightgreen.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest)
<!-- Test count updated from reports/junit.xml on 2025-09-18 (1102 total, 6 skipped → 1096 passed) -->
[![Code Coverage](https://img.shields.io/badge/coverage-86%-green.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest)
<!-- Coverage updated automatically from reports/coverage.xml on 2025-09-18 -->
[![Code Quality](https://img.shields.io/badge/code%20quality-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checking](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](https://mypy-lang.org/)

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

The command-line tool is provided via the `splurge-unittest-to-pytest` console script (or `python -m splurge_unittest_to_pytest.cli`). Below are the supported options and their meanings.

Usage: splurge-unittest-to-pytest [OPTIONS] [PATHS]...

  Convert unittest-style tests to pytest-style tests.

Options:
  --version                       Show the version and exit.
  -o, --output PATH               Output directory for converted files (default: overwrite in place)
  -n, --dry-run                   Show what would be converted without making changes
  -r, --recursive                 Recursively find unittest files in directories
  --encoding TEXT                 Text encoding for reading/writing files (default: utf-8)
  -v, --verbose                   Show detailed output
  -b, --backup PATH               Create backup files in specified directory with .bak extension
  --follow-symlinks / --no-follow-symlinks
                                  Whether to follow symlinked files when discovering test files (default: follow)
  --respect-gitignore             Respect .gitignore patterns when discovering files (default: disabled)
  --setup-methods TEXT            Setup method patterns (comma-separated or multiple flags). Examples: --setup-methods 'setUp,beforeAll' --setup-methods teardown
  --teardown-methods TEXT         Teardown method patterns (comma-separated or multiple flags)
  --test-methods TEXT             Test method patterns (comma-separated or multiple flags)
  --json                          Emit NDJSON per-file results (machine-readable)
  --json-file PATH                Write NDJSON per-file results to the given file (UTF-8). Implies --json.
  --diff                          Show unified diffs for changed files in dry-run mode
  --autocreate / --no-autocreate  Enable or disable autocreation of tmp_path-backed file fixtures when a sibling '<prefix>_content' is present (default: --autocreate)
  --help                          Show this message and exit.

Notes:
- Pass one or more FILE or DIRECTORY paths as positional arguments. If a directory is supplied, use `--recursive` to discover test files.
- When `--output` is omitted the tool overwrites files in place. When provided, converted files are written to the given directory keeping original filenames.
- `--backup` (with a directory path) causes the tool to copy each input file to the backup directory before modifying it (only when not running `--dry-run`). Backups are named like `filename.bak-<hash>` to avoid collisions.
- `--json`/`--json-file` produce NDJSON (newline-delimited JSON) records per-file which is useful for machine processing.
-- Note: normalization of aliased pytest imports is not implemented by the converter; this behavior is planned for a future release.

## CLI Usage Examples

1) Dry-run example (show what would change). This example uses flags common to related tooling that follow similar UX (`--test-root`, `--import-root`, `--repo-root` are used by companion tools such as `splurge_test_namer`):

```bash
# Dry-run: show what would be converted under the current directory (recursive)
splurge-unittest-to-pytest -n -r .

# Example using companion-tool style flags (note: these flags belong to splurge_test_namer; shown here as a usage pattern)
python -m splurge_test_namer.cli --test-root tests --import-root my_package --repo-root /path/to/repo --dry-run
```

2) Apply changes with backups and force semantics (example shows an `apply` style run using `--force --apply` as seen in companion tools). For this project the equivalent is to run without `--dry-run` and optionally supply `--backup` to preserve originals:

```bash
# Convert files in-place, create backups in ./backups, verbose output
splurge-unittest-to-pytest -r --backup ./backups -v PATH/TO/TESTS

# Companion-tool example (apply/force example from splurge_test_namer metadata)
python -m splurge_test_namer.cli --test-root tests --apply --force --backup /path/to/backups
```

If you want the exact `splurge-unittest-to-pytest` equivalents for `--apply`/`--force` semantics: run the command without `-n/--dry-run` to perform the conversion (there is no separate `--apply` flag in this CLI). Use `--backup` to preserve originals and `-v/--verbose` for extra information.


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
- **pytest-xdist**: Parallel test runs
- **ruff**: Unified linting, formatting, and security validation
- **mypy**: Static type checking
- **libcst**: Concrete Syntax Tree (CST)-based code transformation library

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

## Try it: NDJSON output and parsing

You can emit per-file NDJSON records using `--json` or write them to a file with `--json-file`. NDJSON is newline-delimited JSON (one JSON object per line), which is convenient for streaming and machine processing.

```bash
# Write NDJSON results to a file
splurge-unittest-to-pytest -r --json-file results.ndjson PATH/TO/TESTS
```

Small Python example to parse `results.ndjson` and summarize results:

```python
import json

counts = {"converted": 0, "errors": 0, "unchanged": 0}
with open("results.ndjson", "r", encoding="utf-8") as fh:
  for line in fh:
    rec = json.loads(line)
    if rec.get("has_changes"):
      counts["converted"] += 1
    elif rec.get("errors"):
      counts["errors"] += 1
    else:
      counts["unchanged"] += 1

print(counts)
```

## Example: custom method patterns

If your codebase uses non-standard setup/test method names, you can pass additional patterns on the CLI. The flags accept comma-separated lists or may be supplied multiple times.

```bash
# Single flag with comma-separated patterns
splurge-unittest-to-pytest -n --setup-methods "setUp,before_all" --test-methods "should_,test_" tests/

# Multiple flags (equivalent)
splurge-unittest-to-pytest -n --setup-methods setUp --setup-methods before_all --test-methods should_ --test-methods test_ tests/
```

These patterns are used to detect methods that should be considered setup/teardown/test methods during conversion. Patterns may be simple prefixes or full names depending on your project's conventions.
