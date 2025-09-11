# Splurge unittest-to-pytest - Detailed Documentation

## Project Overview

Splurge unittest-to-pytest is a comprehensive Python library and CLI tool for converting unittest-style tests to modern pytest-style tests using libcst (Concrete Syntax Tree) for robust code transformation.

## Architecture

### Core Components

1. **CLI Interface** (`splurge_unittest_to_pytest/cli.py`)
   - Command-line interface built with Click
   - Supports recursive directory processing, dry-run mode, and various output options

2. **Main Conversion Logic** (`splurge_unittest_to_pytest/main.py`)
   - Core conversion functions for files and strings
   - File discovery and processing logic
   - Integration with converter module

3. **Code Transformation** (staged pipeline under `splurge_unittest_to_pytest/stages/`)
    - AST-based code transformation using libcst
    - Assertion conversion, import management, class structure changes
    - Preserves code formatting, comments, and whitespace
    - Legacy transformer implementation has been archived to `contrib/legacy_converter.py` for
       reference; prefer the staged pipeline for conversions.

4. **Exception Handling** (`splurge_unittest_to_pytest/exceptions.py`)
   - Custom exception classes for different error scenarios
   - File not found, permission denied, encoding errors

## Development Environment

-### Prerequisites
- Python 3.10 or higher (tested through Python 3.13)
- Virtual environment (recommended)

### Setup
```bash
# Clone repository
git clone https://github.com/jim-schilling/splurge-unittest-to-pytest
cd splurge-unittest-to-pytest

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Unix/Mac:
source .venv/bin/activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Development Dependencies

#### Core Dependencies
- **libcst (>=1.0.0)**: AST-based code transformation
- **click (>=8.0.0)**: Command-line interface framework

#### Development Dependencies
- **pytest (>=7.0.0)**: Testing framework
- **pytest-cov (>=4.0.0)**: Coverage reporting
- **pytest-mock (>=3.10.0)**: Mocking support for pytest
- **mypy (>=1.0.0)**: Type checking
- **ruff (>=0.1.0)**: Unified linting and formatting

### Code Quality Tools

The project uses **ruff** as a unified tool for:
- Code linting (replacing flake8)
- Code formatting (replacing black)
- Import sorting (replacing isort)

```bash
# Run all quality checks
ruff check .
ruff format .

# Type checking
mypy splurge_unittest_to_pytest/
```

## Testing Strategy

### Test Organization
```
tests/
├── unit/                    # Unit tests
│   ├── test_cli.py         # CLI interface tests
│   ├── test_converter.py   # Code transformation tests
│   └── test_main.py        # Main functionality tests
├── integration/            # Integration tests (future)
├── e2e/                    # End-to-end tests (future)
└── data/                   # Test data files
```

### Test Infrastructure Modernization (2025.0.0)

#### pytest-mock Integration
- Replaced `unittest.mock` with `pytest-mock` fixtures
- All test methods now accept `mocker` parameter
- Better integration with pytest's fixture system

#### Modern Test Fixtures
- Migrated from `tempfile.NamedTemporaryFile` to `pytest.tmp_path` fixture
- Automatic cleanup and better test isolation
- Removed manual file/directory cleanup code

#### pytest Configuration
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=splurge_unittest_to_pytest --cov-report=term-missing"
pythonpath = ["."]
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=splurge_unittest_to_pytest

# Run specific test file
pytest tests/unit/test_main.py

# Run specific test
pytest tests/unit/test_main.py::TestFileOperations::test_convert_file_in_place

# Run tests matching pattern
pytest -k "test_convert"
```

## Code Conversion Process

### Supported Transformations

#### 1. Assertion Conversion
| unittest Assertion | pytest Equivalent |
|-------------------|------------------|
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

#### 2. Class Structure Changes
- Removes `unittest.TestCase` inheritance
- Converts `setUp()` methods to `@pytest.fixture` decorated `setup_method()`
- Converts `tearDown()` methods to `@pytest.fixture(autouse=True)` decorated `teardown_method()` with yield pattern

#### 3. Import Management
- Removes `import unittest` and `from unittest import ...` statements
- Adds `from pytest import *` when pytest features are used
- Preserves other imports and their formatting

##### Known-bad `unittest.mock` names mapping

The converter includes a small curated mapping of `unittest.mock` names that
should not be preserved as `from unittest.mock import <name>` during conversion
because they are not intended to be top-level importable symbols or are often
misused in source files during automated conversion.

Location
- `splurge_unittest_to_pytest/data/known_bad_mock_names.json` — a JSON object
   whose keys are problematic names and whose values are short reasons.

Why this exists
- Some constructs (for example `side_effect`) are attributes set on mock
   instances rather than exported module-level symbols. Leaving them in
   `from unittest.mock import ...` lists causes ImportError after conversion.
- Keeping a curated list avoids over-eager rewrites while still ensuring the
   converted output imports cleanly at module import time.

Format example
```
{
   "side_effect": "attribute on bound mock instances, not a top-level import",
   "autospec": "argument name for patching utilities, not an importable symbol"
}
```

How to extend
- To add or remove entries, update the JSON file under `splurge_unittest_to_pytest/data/`.
- The transformer loads the mapping at runtime; changes to this file take effect
   immediately on the next conversion run (no code changes required).
- When adding entries, prefer a short human-readable reason string as the value.

Fallback behavior
- If the mapping cannot be loaded for any reason (packaging, file access), the
   transformer uses a small built-in fallback set to remain conservative and safe.

Maintenance notes
- Keep the mapping minimal and evidence-based — add names only when practical
   conversion cases demonstrate an ImportError or runtime problem.
- Consider adding a unit test for each newly added mapping entry that verifies
   the transformer rewrites the corresponding `from unittest.mock` import.

### Conversion Algorithm

1. **Parse Source Code**: Use libcst to parse Python code into AST
2. **Identify unittest Patterns**: Detect unittest-specific constructs
3. **Transform Assertions**: Convert unittest assertions to pytest assertions
4. **Update Class Structure**: Remove TestCase inheritance and convert setup/teardown methods
5. **Manage Imports**: Remove unittest imports, add pytest imports as needed
6. **Preserve Formatting**: Maintain original code style, comments, and whitespace
7. **Generate Output**: Produce converted code with all transformations applied

## CLI Usage Examples

### Basic Usage
```bash
# Convert single file
splurge-unittest-to-pytest test_example.py

# Convert multiple files
splurge-unittest-to-pytest test_*.py

# Recursive directory conversion
splurge-unittest-to-pytest --recursive tests/
```