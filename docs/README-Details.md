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

### Advanced Options
```bash
# Dry run to preview changes
splurge-unittest-to-pytest --dry-run --recursive tests/

# Convert to different directory
splurge-unittest-to-pytest --output-dir converted/ test_*.py

# Specify encoding
splurge-unittest-to-pytest --encoding utf-8 test_file.py

# Verbose output
splurge-unittest-to-pytest --verbose --recursive tests/

# Create backups before conversion
splurge-unittest-to-pytest --backup backups/ test_*.py
```

### Compatibility and Discovery Notes

- --compat / --no-compat
   - The CLI exposes a `--compat` flag (default) which emits a small autouse fixture that
      attaches generated fixtures to the original unittest-style `self` test instance where
      applicable. This preserves code that referenced `self.<name>` inside tests after
      conversion. Use `--no-compat` to disable this behavior if you prefer pure pytest idioms
      and to avoid emitting the compatibility glue.

### Note on legacy transformer

- The legacy `UnittestToPytestTransformer` implementation has been removed from the
   public API; the staged pipeline is now the authoritative conversion engine. Tests
   and examples that previously used the legacy transformer should use `convert_string`
   (engine='pipeline') or the `PatternConfigurator` helper for pattern configuration.

### Integration test

- An end-to-end integration test verifies converted modules are executable and that
   autouse fixtures attach values to the converted test instance when `--compat` is used.

- Backups
   - Use `--backup <dir>` to create a copy of each file before it is modified. Backups are
      saved as `<filename>.bak` in the provided directory. Backups are not created during
      `--dry-run`.

- Discovery robustness
   - The converter will skip `__pycache__` directories during recursive discovery and will
      treat unreadable files (encoding/permission errors) as non-unittest files so that
      discovery continues. Any files skipped for access reasons will be reported when `--verbose`
      is used or in the CLI summary.

### Troubleshooting

- No changes detected
   - If the tool reports "No changes needed" the source file either contains no unittest
      constructs the converter recognizes, or conversion was intentionally disabled via
      `--no-compat` or custom method patterns. Try a dry-run with `--verbose` to see more
      diagnostic information.

- Files skipped during discovery
   - If a directory appears to be skipped, ensure you are using `--recursive` and that
      file permissions allow reading. `__pycache__` directories are ignored by design.

- Unexpected errors during conversion
   - Run the converter with `--dry-run --verbose` to see parse and transformation errors.
   - If you discover a transformation bug, please open an issue and include the minimal
      test file that reproduces the problem; see `docs/issue-u2p.md` for existing reports.

### Custom Method Patterns

Splurge supports configurable method name patterns to accommodate different testing frameworks and custom conventions. This feature allows you to specify custom patterns for setup, teardown, and test methods.

#### Default Patterns

The converter includes these default patterns:

**Setup Methods:**
- `setUp`, `set_up`, `setup`, `setup_method`, `setUp_method`
- `before_each`, `beforeEach`, `before_test`, `beforeTest`

**Teardown Methods:**
- `tearDown`, `tear_down`, `teardown`, `teardown_method`, `tearDown_method`
- `after_each`, `afterEach`, `after_test`, `afterTest`

**Test Methods:**
- `test_`, `test`, `should_`, `when_`, `given_`, `it_`, `spec_`

#### Custom Pattern Configuration

Use the following CLI options to specify custom method patterns:

```bash
# Comma-separated patterns
splurge-unittest-to-pytest --setup-methods "setUp,beforeAll,setup_class" test.py

# Multiple flag usage
splurge-unittest-to-pytest --setup-methods setUp --setup-methods beforeAll test.py

# Configure all method types
splurge-unittest-to-pytest --setup-methods "setUp,beforeAll" \
                --teardown-methods "tearDown,afterAll" \
                --test-methods "test_,it_,spec_" test.py
```

#### Pattern Matching Features

- **Case-insensitive matching**: `setUp` matches `setup`, `SETUP`, etc.
- **CamelCase/Snake_case support**: `beforeAll` matches `before_all` and vice versa
- **Flexible syntax**: Supports both prefix patterns (`test_`) and exact patterns (`setUp`)
- **Whitespace handling**: Automatically trims whitespace from pattern arguments
- **Duplicate removal**: Eliminates duplicate patterns while preserving order

#### Pattern Examples

```bash
# JavaScript testing frameworks
splurge-unittest-to-pytest --setup-methods "beforeEach,beforeAll" \
                --teardown-methods "afterEach,afterAll" \
                --test-methods "describe_,it_,context_" test.js

# Ruby RSpec style
splurge-unittest-to-pytest --setup-methods "before,before_each" \
                --teardown-methods "after,after_each" \
                --test-methods "describe_,it_,context_" test.rb

# Custom framework patterns
splurge-unittest-to-pytest --setup-methods "my_setup,custom_setup" \
                --teardown-methods "my_teardown,custom_teardown" \
                --test-methods "spec_,feature_,scenario_" test.py
```

#### Pattern Parsing Details

The CLI argument parser handles various edge cases:

- **Leading/trailing spaces**: `"  setUp  "` → `["setUp"]`
- **Empty values**: `"setUp,,beforeAll"` → `["setUp", "beforeAll"]`
- **Only whitespace**: `"  "` → `[]` (ignored)
- **Trailing commas**: `"setUp,beforeAll,"` → `["setUp", "beforeAll"]`
- **Leading commas**: `",setUp,beforeAll"` → `["setUp", "beforeAll"]`
- **Duplicate patterns**: `("setUp", "setUp")` → `["setUp"]` (deduplicated)

#### Integration with Conversion Process

Custom patterns are applied during the AST transformation phase:

1. **Method Detection**: Uses configured patterns to identify setup/teardown/test methods
2. **Parameter Removal**: Removes `self`/`cls` parameters based on method type detection
3. **Fixture Conversion**: Converts setup/teardown methods to pytest fixtures
4. **Reference Removal**: Removes `self.`/`cls.` references from converted methods

This ensures that custom method patterns work seamlessly with all existing conversion features.

## Library API Usage

### Basic Conversion
```python
from splurge_unittest_to_pytest import convert_string, convert_file

# Convert code string
result = convert_string(unittest_code)
if result.has_changes:
    print("Conversion successful!")
    print(result.converted_code)

# Convert file
result = convert_file("test_unittest.py", "test_pytest.py")
```

### Advanced Usage
```python
from splurge_unittest_to_pytest import find_unittest_files
from pathlib import Path

# Find all unittest files in directory
unittest_files = find_unittest_files(Path("tests/"))
print(f"Found {len(unittest_files)} unittest files")

# Process each file
for file_path in unittest_files:
    result = convert_file(file_path)
    if result.has_changes:
        print(f"Converted: {file_path}")
    if result.errors:
        print(f"Errors in {file_path}: {result.errors}")
```

## Error Handling

The library provides comprehensive error handling for various scenarios:

- **FileNotFoundError**: When input file doesn't exist
- **PermissionDeniedError**: When file cannot be read/written
- **EncodingError**: When file encoding issues occur
- **ConversionError**: When code transformation fails

## Performance Considerations

- **AST-based Processing**: Uses libcst for efficient, accurate code transformation
- **Memory Efficient**: Processes files one at a time to minimize memory usage
- **Incremental Conversion**: Only modifies code that needs changing
- **Preserves Performance**: Converted tests maintain same execution characteristics

## Future Enhancements

### Planned Features
- Support for additional unittest assertion methods
- Custom fixture generation for complex setup scenarios
- Integration with popular testing frameworks
- Plugin system for custom transformations
- GUI interface for visual conversion

### Testing Improvements
- Integration test suite
- End-to-end test scenarios
- Performance benchmarking
- Cross-platform testing

## Contributing Guidelines

### Code Standards
- Follow PEP 8 style guidelines
- Use type annotations for all function signatures
- Write comprehensive docstrings
- Add tests for all new functionality

### Development Workflow
1. Create feature branch from `main`
2. Make changes with tests
3. Run full test suite: `pytest`
4. Run code quality checks: `ruff check . && ruff format . && mypy .`
5. Update documentation as needed
6. Submit pull request

### Testing Requirements
- All new code must have corresponding tests
- Maintain or improve code coverage
- Tests must pass on all supported Python versions (up through Python 3.13)
- Include both positive and negative test cases

## License and Attribution

This project is licensed under the MIT License. See LICENSE file for details.

### Acknowledgments
- **libcst**: For robust Python code transformation capabilities
- **pytest**: For the modern testing framework this tool converts to
- **Click**: For excellent CLI framework
- **pytest-mock**: For enhanced mocking capabilities in tests

## Support and Maintenance

For support, bug reports, or feature requests:
- GitHub Issues: https://github.com/jim-schilling/splurge-unittest-to-pytest/issues
- Documentation: This detailed README and inline code documentation
- Tests: Comprehensive test suite demonstrating all functionality