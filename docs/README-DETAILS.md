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
      - The staged pipeline is the canonical conversion implementation; prefer the
         public API (`convert_string`, `convert_file`) which invokes the pipeline.

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

## Recent migration notes (2025-09-13 → 2025-09-14)

This repository recently completed a migration to remove legacy compatibility shims and to modernize the test surface. The following summarizes what changed and why:

 Legacy compatibility/autouse helpers were removed from production code. The staged pipeline is the canonical converter and produces strict pytest-native (strict-only) output by default as of the 2025.2.0 release.
 If you maintain tooling or CI that relied on older legacy compatibility flags, update your workflows to accept strict pytest-native output. Key migration guidance:

 Files that relied on the legacy compatibility flag to preserve TestCase class structure will now be emitted as top-level pytest functions and fixtures. If you need to preserve class-style organization, wrap converted functions into classes manually or use grouping helpers in your test suite.
 Update any automation that parsed textual output of converted files (for example golden-file checks) to accept the stricter pytest-native formatting: fixtures are emitted with two blank lines before top-level fixtures and `@pytest.fixture` decorated functions are inserted before tests.
 Replace references to legacy compatibility flags (for example --compat) or compat=True/False in CI scripts and programmatic calls with direct use of the staged pipeline (`convert_string`, `convert_file`) which now implements strict behavior.

 Run `pytest -n 7` locally after updating your tooling to ensure converted modules pass in your target environment.
- The local `build/` directory (generated artifacts) was removed from the working tree and `build/` is ignored via `.gitignore` to prevent accidental commits of generated files.

Verification performed locally during the migration:

- ruff format/check: passed (a few files were reformatted during the change)
- mypy: no type errors reported for the package
- pytest (unit tests): local unit test run passed (859 passed, 1 skipped) and full-suite runs performed earlier reported 874 passed, 4 skipped. Coverage summary printed (~86% project coverage during the run).

If you maintain tooling or CI that relied on older compat flags, update your workflows to use the staged pipeline and the modernized CLI semantics.

## Feature branch: update-2025.1.1 (branch: update-2025.1.1)

This documentation block summarizes the purpose and scope of the feature branch
`update-2025.1.1`. It mirrors the entry added to `CHANGELOG.md` and provides a
few practical notes for reviewers and consumers of the branch.

- Purpose: prepare the repository for the 2025.1.1 patch release by bumping
   package metadata, regenerating generator goldens, and applying minor
   packaging consistency fixes.
- Key changes:
   - Package metadata/version bumped to `2025.1.1`.
   - Generator goldens were regenerated to reflect improved literal-preservation
      and NamedTuple bundling behavior; sample goldens were regenerated from
      `tests/data/samples`.
   - Small packaging and metadata consistency fixes to improve installability and
      CI reproducibility.
- Verification done locally:
   - Formatting: `ruff format`/`ruff check` applied and recorded minor reformatting.
   - Type checks: `mypy` reported no type errors for the package.
   - Tests: local unit test runs used during verification (representative runs):
      - unit-only run: 859 passed, 1 skipped
      - earlier full-suite runs reported: 874 passed, 4 skipped
      These numbers are included for traceability; CI may report slightly
      different counts depending on the environment and optional dependency
      availability.
- Merge guidance:
   - This branch contains no public API breaking changes beyond previously
      announced removals. Consumers using the public API (`convert_string`,
      `convert_file`) should not need changes; if your tooling relied on the
      removed compatibility flags, update it to use the staged pipeline.
   - After merging, verify CI on the main branch to ensure the regenerated
      goldens are accepted in downstream workflows that compare against them.

If you have questions about the goldens or the literal-preservation changes,
see `tools/check_generated.py` and `tests/goldens/` for sample comparisons.

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

### ASSERTIONS_MAP (developer note)

The assertion conversion functions are centrally registered in
`splurge_unittest_to_pytest.converter.assertions.ASSERTIONS_MAP`.

- Purpose: single source-of-truth for mapping unittest assertion method names
   (e.g. `"assertEqual"`) to the converter function that produces the
   equivalent pytest AST node.
- Where to add new conversions: edit `splurge_unittest_to_pytest/converter/assertions.py`
   and add the new converter function plus an entry to `ASSERTIONS_MAP`.
- Tests: when adding a new mapping, add a small unit test under `tests/unit/`
   that asserts `convert_assertion` returns the expected AST node for the new
   assertion name.

This central map is used by `converter.assertion_dispatch.convert_assertion` to
perform fast lookups and keeps the dispatcher thin.

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

## Diagnostics and Smoke Test Behavior

Diagnostics are opt-in via the environment variable `SPLURGE_ENABLE_DIAGNOSTICS`.
When enabled the pipeline will create a per-run diagnostics directory containing
timestamped snapshots of the module before, during, and after each stage. This
is intended for debugging conversions and should not be enabled in normal CI
runs as it will create temporary files on disk.

The integration "smoke" harness used by the test-suite is intentionally
compile-only. Some example files in `examples/` depend on optional third-party
packages (for example `parameterized`) that are not required for the
converter library itself. To avoid test failures caused by executing example
code that imports optional dependencies the smoke test only parses/compiles the
converted output rather than executing it. This keeps CI robust while still
validating the conversion output is syntactically correct.

### Diagnostics root override

If you prefer diagnostics artifacts to be written to a specific location (for
example a CI-provided workspace directory), set the `SPLURGE_DIAGNOSTICS_ROOT`
environment variable to the desired path. When set, the diagnostics directory
will be created under that path instead of the system temp directory.

Example (Unix):

```bash
export SPLURGE_ENABLE_DIAGNOSTICS=1
export SPLURGE_DIAGNOSTICS_ROOT="$CI_WORKSPACE/tmp"
```

Example (Windows PowerShell):

```powershell
$env:SPLURGE_ENABLE_DIAGNOSTICS = '1'
$env:SPLURGE_DIAGNOSTICS_ROOT = 'C:\ci\workspace\tmp'
```

### Inspecting diagnostics artifacts

When diagnostics are enabled the pipeline creates a per-run directory containing
timestamped snapshots and a small marker file. The marker file contains the
absolute path to the diagnostics directory and is useful when locating the
artifacts on CI workers or local development machines.

Example marker file name: `splurge-diagnostics-2025-09-12_14-23-47`

Quick manual inspection (Windows PowerShell):

```powershell
# List diagnostic dirs under override or temp
Get-ChildItem -Path $env:SPLURGE_DIAGNOSTICS_ROOT -Directory

# Read marker file
Get-Content -Path (Get-ChildItem -Path $env:SPLURGE_DIAGNOSTICS_ROOT -Filter "splurge-diagnostics-*" -File)
```

Helper script `tools/print_diagnostics.py` is provided to discover and print
the most recent diagnostics directory and its marker file. It can be run with
an explicit `--root` argument or will use `SPLURGE_DIAGNOSTICS_ROOT` / system
temp when not provided.

CI notes
--------

To make diagnostics easier to find in CI we've added a small debug step in the
`.github/workflows/upload-diagnostics.yml` workflow which prints the value of
`SPLURGE_DIAGNOSTICS_ROOT` and lists the directory contents in the job logs.
This helps correlate uploaded artifacts with job logs and makes local
investigation straightforward. The workflow also sets a workspace-local
diagnostics root (for example `$GITHUB_WORKSPACE/tmp_diagnostics`) so the
artifact upload can use a deterministic path.

Using the helper
----------------

The `splurge-print-diagnostics` console script is installed by the package and
is a small convenience wrapper around the module runner. Use it like this after
installing the package in a virtualenv or CI image:

```bash
splurge-print-diagnostics
# or
python -m splurge_unittest_to_pytest.print_diagnostics
```

You can also pass `--root <path>` to inspect a specific diagnostics root.

Example
-------

Assuming diagnostics were written to `C:\ci\workspace\tmp_diagnostics` you can run:

```powershell
splurge-print-diagnostics --root C:\ci\workspace\tmp_diagnostics
```

Sample output:

```
Found diagnostics run: splurge-diagnostics-2025-09-12_14-23-47
Marker file: C:\ci\workspace\tmp_diagnostics\splurge-diagnostics-2025-09-12_14-23-47
Files:
   - marker
   - snapshots/module_before_stage1.py
   - snapshots/module_after_stage1.py
   - snapshots/module_after_stage2.py
```

This output prints the most recent diagnostics run directory, the marker file
path, and a short file listing to help you locate snapshots quickly.

## Strict pytest output

This tool emits strict, pytest-native code. Compatibility mode has been removed
and the converter uses a single staged-pipeline implementation.

- Unittest classes and lifecycle methods (`setUp`/`tearDown`) are converted into pytest fixtures or dropped where appropriate
- No autouse `_attach_to_instance` fixture is injected
- Top-level pytest tests are generated that accept fixtures directly

### CLI examples

```bash
# Convert a directory to pytest style
splurge-unittest-to-pytest --recursive tests/

# Convert files to an output directory
splurge-unittest-to-pytest -o converted/ tests/data/*.bak.txt
```

### Python API

```python
from splurge_unittest_to_pytest.main import convert_string

res = convert_string(src_code)
print(res.converted_code)
```

### Notes

Compatibility mode has been removed and documentation/tests were updated to reflect the simplified public API and CLI behavior.