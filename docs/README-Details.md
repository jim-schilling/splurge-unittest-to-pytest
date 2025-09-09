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

3. **Code Transformation** (`splurge_unittest_to_pytest/converter.py`)
   - AST-based code transformation using libcst
   - Assertion conversion, import management, class structure changes
   - Preserves code formatting, comments, and whitespace

4. **Exception Handling** (`splurge_unittest_to_pytest/exceptions.py`)
   - Custom exception classes for different error scenarios
   - File not found, permission denied, encoding errors

## Development Environment

### Prerequisites
- Python 3.10 or higher
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
splurge-convert test_example.py

# Convert multiple files
splurge-convert test_*.py

# Recursive directory conversion
splurge-convert --recursive tests/
```

### Advanced Options
```bash
# Dry run to preview changes
splurge-convert --dry-run --recursive tests/

# Convert to different directory
splurge-convert --output-dir converted/ test_*.py

# Specify encoding
splurge-convert --encoding utf-8 test_file.py

# Verbose output
splurge-convert --verbose --recursive tests/
```

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
- Tests must pass on all supported Python versions
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