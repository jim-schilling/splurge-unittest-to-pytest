# splurge-unittest-to-pytest — Detailed Reference

This document provides a comprehensive reference for the tool including
features, CLI flags, examples, programmatic API usage, safety notes, and
developer guidance.

Table of contents
- Overview
- Features
- Supported unittest to pytest conversion candidates
- CLI reference
- YAML Configuration File Format
- Examples (CLI and programmatic)
- Programmatic API
- Safety and limitations
- Developer notes

Overview
--------
``splurge-unittest-to-pytest`` converts Python ``unittest``-style tests to
``pytest``-style tests using conservative, AST/CST-based transformations
implemented with ``libcst``. The project features a **multi-pass analyzer**
that intelligently analyzes test patterns and applies transformations with
high confidence, preserving semantics where code mutates accumulators or
depends on loop ordering. The project aims to preserve test semantics and
readability while offering convenient preview and reporting options.

Features
--------
- **Multi-pass analyzer** that intelligently analyzes test patterns and applies
  transformations with high confidence, preserving semantics where code mutates
  accumulators or depends on loop ordering.
- **Enhanced pattern support**: Custom test prefixes (``spec_``, ``should_``, ``it_``),
  nested test classes, custom setup methods, and advanced exception handling.
- **Intelligent configuration system**: Automatically analyzes your project structure,
  test patterns, and codebase characteristics to provide tailored migration suggestions
  and configuration recommendations.
- **Smart error recovery**: Comprehensive error handling with intelligent recovery
  strategies, detailed error reporting, and suggestions for resolving configuration issues.
- **Configuration templates**: Pre-built configuration templates for common migration
  scenarios including CI/CD integration, large codebase migrations, and specialized testing frameworks.
- **Interactive configuration builder**: Step-by-step guided configuration process
  that analyzes your project and builds optimal settings through interactive prompts.
- **Comprehensive field metadata**: Rich metadata system providing detailed help,
  validation rules, examples, and cross-references for all configuration options.
- CST-based transformations using ``libcst`` for stable, semantics-preserving edits.
- Preserves class-structured tests that inherit from ``unittest.TestCase`` by default to
	maintain class scope and fixtures unless a conversion is explicitly requested.
- Converts common ``unittest`` assertions to Python ``assert`` statements or
	``pytest`` helpers when the conversion is safe and conservative.
- Merges ``setUp``/``tearDown`` into pytest fixtures where appropriate.
- **Configurable test discovery**: Supports custom test method prefixes and nested
  test class structures for modern testing frameworks.
- **Advanced setup/teardown detection**: Recognizes custom setup method patterns
  beyond standard ``setUp``/``tearDown``.
- **Enhanced exception handling**: Supports custom exception types, exception chaining,
  and advanced warning assertions.
- Dry-run modes: show generated code, unified diffs (``--diff``), or file lists (``--list``).
- Generated code is always formatted with ``isort`` and ``black`` before writing.
- Import optimization and safe removal of unused ``unittest`` imports while
	detecting dynamic import patterns to avoid unsafe removals.

Intelligent Configuration System
---------------------------------
The tool includes an advanced configuration system that intelligently analyzes your project and provides tailored recommendations for optimal migration settings.

### Intelligent Suggestions
Use ``--suggestions`` to get intelligent configuration suggestions based on your project's characteristics:

```bash
# Get suggestions for your project
python -m splurge_unittest_to_pytest.cli migrate tests/ --suggestions
```

The system analyzes:
- Project structure and test organization
- Test method naming patterns
- Code complexity and file sizes
- Import patterns and dependencies
- Custom setup/teardown patterns

### Use Case Analysis
Use ``--use-case-analysis`` to get a comprehensive analysis of your project's migration needs:

```bash
# Analyze your project's use case
python -m splurge_unittest_to_pytest.cli migrate tests/ --use-case-analysis
```

This provides:
- Detected migration complexity level
- Recommended configuration templates
- Potential challenges and solutions
- Performance optimization suggestions

### Configuration Templates
Pre-built templates for common scenarios:

```bash
# List available templates
python -m splurge_unittest_to_pytest.cli migrate --list-templates

# Use a specific template
python -m splurge_unittest_to_pytest.cli migrate tests/ --template ci_integration
```

Available templates:
- ``basic_migration``: Standard unittest to pytest conversion
- ``ci_integration``: Optimized for CI/CD pipelines with parallel processing
- ``large_codebase``: Handles large projects with memory optimization
- ``bdd_framework``: Specialized for BDD-style tests (spec_, should_, it_)
- ``legacy_system``: Conservative settings for legacy codebases

### Interactive Configuration Builder
For complex projects, use the interactive builder to create optimal configurations:

```bash
# Start interactive configuration
python -m splurge_unittest_to_pytest.cli init-config --interactive my-config.yaml
```

The builder will:
- Analyze your project structure
- Ask targeted questions about your needs
- Generate a comprehensive configuration file
- Provide explanations for each setting

### Field Help System
Get detailed help for any configuration field:

```bash
# Get help for a specific field
python -m splurge_unittest_to_pytest.cli migrate --field-help max_file_size_mb
```

Each field includes:
- Detailed description
- Valid value ranges
- Default values
- Usage examples
- Related configuration options

### Configuration Documentation Generation
Generate comprehensive documentation for all configuration options:

```bash
# Generate markdown documentation
python -m splurge_unittest_to_pytest.cli migrate --generate-docs markdown

# Generate HTML documentation
python -m splurge_unittest_to_pytest.cli migrate --generate-docs html
```

### Smart Error Recovery
The system provides intelligent error recovery with:
- Detailed error categorization
- Suggested fixes for common issues
- Configuration validation with helpful messages
- Recovery strategies for corrupted configurations

Supported unittest to pytest conversion candidates
-----------------------------------------------
This section summarizes the common ``unittest`` APIs and patterns the tool
will attempt to convert automatically. The transformations are conservative
— we only rewrite constructs when we can preserve semantics with high
confidence. Where conversions are ambiguous the tool prefers a readable
fallback and records warnings in the migration report.

1. Assertion rewriting
	- assertEqual(a, b) -> assert a == b
	- assertNotEqual(a, b) -> assert a != b
	- assertTrue(x) -> assert x
	- assertFalse(x) -> assert not x
	- assertIs(a, b) -> assert a is b
	- assertIsNot(a, b) -> assert a is not b
	- assertIsNone(x) -> assert x is None
	- assertIsNotNone(x) -> assert x is not None
	- assertIn(a, b) -> assert a in b
	- assertNotIn(a, b) -> assert a not in b
	- assertGreater(a, b) / assertLess / assertGreaterEqual / assertLessEqual -> corresponding comparison asserts
	- assertRaises(Exception, callable, *args, **kwargs) -> use ``with pytest.raises(Exception): callable(*args, **kwargs)`` when the call site is simple
	- assertRaises as a context manager -> ``with pytest.raises(Exception):`` (preserved)
	- assertRaisesRegex -> ``with pytest.raises(Exception, match="regex"):``
	- **assertWarns -> ``with pytest.warns(WarningClass):`` when available**
	- **assertWarnsRegex -> ``with pytest.warns(WarningClass, match="regex"):``**
	- **Custom exception types**: Preserves custom exception classes (e.g., ``CustomError``) in transformations
	- **Exception chaining**: Supports ``assertRaises`` with additional callable arguments
	- **Custom warning types**: Preserves custom warning classes in ``assertWarns`` transformations

2. Test lifecycle and fixtures
	- ``setUp`` / ``tearDown`` methods -> converted into function-scoped ``pytest`` fixtures (``setup_method``/``teardown_method`` style is preserved when safer)
	- ``setUpClass`` / ``tearDownClass`` -> converted to class/module scoped fixtures where possible; conversion is conservative to avoid changing sharing semantics
	- ``setUpModule`` / ``tearDownModule`` -> converted to module-scoped fixtures
	- **Custom setup method detection**: Recognizes various setup method naming patterns:
	  - ``setup_method``, ``teardown_method`` (pytest-style)
	  - ``before_each``, ``after_each`` (common testing patterns)
	  - ``before``, ``after``, ``before_all``, ``after_all``
	  - ``initialize``, ``cleanup``, ``prepare``, ``finalize``
	  - ``set_up``, ``tear_down`` (snake_case variants)

3. Test discovery and structure
	- Tests in ``unittest.TestCase`` subclasses can be preserved as methods on the class or (optionally) converted into top-level ``pytest`` test functions when the transformation is safe and keeps semantics intact
	- **Custom test method prefixes**: Supports configurable test prefixes beyond ``test_`` (e.g., ``spec_``, ``should_``, ``it_``) for modern testing frameworks like BDD-style tests
	- **Nested test classes**: Properly handles test classes nested within other test classes, preserving the hierarchical structure in the transformed output
	- **Custom setup method detection**: Recognizes various setup method naming patterns beyond standard ``setUp``/``tearDown`` (e.g., ``setup_method``, ``before_each``, ``cleanup``)
	- ``subTest`` blocks: the transformer will attempt conservative conversions to parametrization only when the subtest usage is simple (e.g., iterating over a static list of inputs). Complex uses of loop variables, nested subtests, or dynamically generated cases will be left as-is and a warning will be emitted suggesting manual refactor to ``pytest.mark.parametrize``.

4. Test decorators and markers
	- ``@unittest.skip(reason)`` -> ``@pytest.mark.skip(reason=...)``
	- ``@unittest.skipIf(cond, reason)`` / ``@unittest.skipUnless`` -> ``pytest.mark.skipif`` conversions when the condition is a simple expression
	- ``@unittest.expectedFailure`` -> ``@pytest.mark.xfail`` (note: semantics differ; the tool documents any differences in the report)
	- **Custom exception types**: Preserves custom exception classes (e.g., ``CustomError``) in ``assertRaises`` transformations
	- **Exception chaining**: Supports ``assertRaises(Exception, func, arg1, arg2)`` with additional callable arguments
	- **Custom warning types**: Preserves custom warning classes in ``assertWarns`` transformations

5. Other helpers and patterns
	- ``self.assertLogs`` -> attempt to use ``caplog`` or ``pytest`` logging helpers when the context is simple; otherwise preserved with a note
	- ``unittest.mock.patch`` usage is preserved; simple context-manager or decorator uses may be converted to the same pattern under ``pytest`` (no behavioral change)
	- Common helper methods on ``TestCase`` that are purely assertion wrappers may be inlined when safe to improve readability; otherwise retained

Limitations and caveats
-----------------------
- Dynamic or metaprogrammed tests (tests generated at runtime, complex class factory patterns) are not reliably converted and are typically left unchanged.
- Custom ``TestCase`` subclasses that override discovery, run logic, or implement non-trivial helpers may prevent safe automatic conversion.
- The **multi-pass analyzer** intelligently handles ``subTest`` conversions: it uses sophisticated pattern analysis to determine when to apply ``parametrize`` vs ``subtests`` transformations, preserving semantics where code mutates accumulators or depends on loop ordering.
- Any conversion that may alter test ordering, scoping, or shared mutable state (for example, complex class-level fixtures) is avoided or flagged for manual review.
- The semantics of ``expectedFailure`` differ slightly between ``unittest`` and ``pytest.xfail``; when a conversion is applied the tool documents the change in the migration report so users can verify intent.

Examples
--------
Simple assertion conversion:

```py
# Before (unittest)
self.assertEqual(result, expected)

# After (pytest)
assert result == expected
```

Simple assertRaises conversion (callable form -> context manager form):

```py
# Before
self.assertRaises(ValueError, func, arg)

# After
with pytest.raises(ValueError):
	 func(arg)
```

Subtest -> parametrize (only when safe):

```py
# Before
for inp, expected in [(1, 2), (3, 4)]:
	 with self.subTest(inp=inp):
		  self.assertEqual(func(inp), expected)

# After (parametrize)
@pytest.mark.parametrize("inp,expected", [(1, 2), (3, 4)])
def test_func(inp, expected):
	 assert func(inp) == expected
```

Custom test prefixes:

```py
# Before (spec_ prefix)
class TestCalculator(unittest.TestCase):
    def spec_should_add_numbers(self):
        self.assertEqual(add(1, 2), 3)

# After (preserved with spec_ prefix)
class TestCalculator:
    def spec_should_add_numbers(self):
        assert add(1, 2) == 3
```

Nested test classes:

```py
# Before
class TestAPI(unittest.TestCase):
    def test_basic_endpoint(self):
        pass

    class TestAuthentication(unittest.TestCase):
        def test_login_endpoint(self):
            pass

# After (preserved structure)
class TestAPI:
    def test_basic_endpoint(self):
        pass

    class TestAuthentication:
        def test_login_endpoint(self):
            pass
```

Custom setup methods:

```py
# Before
class TestExample(unittest.TestCase):
    def setup_method(self):
        self.value = 42

    def before_each(self):
        self.counter = 0

# After (preserved as-is)
class TestExample:
    def setup_method(self):
        self.value = 42

    def before_each(self):
        self.counter = 0
```

Enhanced exception handling:

```py
# Before
class CustomError(Exception):
    pass

class TestExample(unittest.TestCase):
    def test_custom_exception(self):
        def func():
            raise CustomError("custom message")

        self.assertRaises(CustomError, func)

    def test_warning_with_args(self):
        def func(message, category):
            warnings.warn(message, category)

        self.assertWarnsRegex(UserWarning, func, r"test \w+", "test message", UserWarning)

# After
class CustomError(Exception):
    pass

class TestExample:
    def test_custom_exception(self):
        def func():
            raise CustomError("custom message")

        with pytest.raises(CustomError):
            func()

    def test_warning_with_args(self):
        def func(message, category):
            warnings.warn(message, category)

        with pytest.warns(UserWarning, match=r"test \w+"):
            func("test message", UserWarning)
```

CLI reference
-------------
All flags are available on the ``migrate`` command. Summary below; use
``--help`` for the authoritative list.

## File Discovery and Input
- ``-d, --dir DIR``: Root directory for input discovery.
- ``-f, --file PATTERN``: Glob pattern(s) to select files (repeatable). Default: ``test_*.py``.
- ``-r, --recurse / --no-recurse``: Recurse directories (default: recurse).

## Output and File Handling
- ``-t, --target-root DIR``: Root directory to write outputs.
- ``--backup-root DIR``: Root directory for backup files when recursing. When specified, backups preserve folder structure. By default, backups are created next to the original files.
- ``--skip-backup``: Skip creating a ``.backup`` copy of originals when writing (presence-only flag). By default the tool creates a ``.backup`` file next to the original when writing; if a ``.backup`` file already exists it will be preserved and not overwritten.
- ``--ext EXT``: Override the target file extension (e.g. ``.py`` or ``.txt``). Defaults to preserving the original extension.
- ``--suffix SUFFIX``: Append suffix to target filename stem when writing (default: empty string).
- ``--preserve-encoding / --no-preserve-encoding``: Preserve original file encoding when writing output (default: preserve).

## Formatting and Code Quality
- ``--line-length N``: Max line length used by formatters (default: 120).
- ``--format / --no-format``: Format output code with black and isort (default: format).

## Import Handling
- ``--remove-imports / --no-remove-imports``: Remove unused unittest imports after transformation (default: remove).
- ``--preserve-import-comments / --no-preserve-import-comments``: Preserve comments in import sections (default: preserve).

## Transform Selection
- ``--transform-assertions / --no-transform-assertions``: Transform unittest assertions to pytest assertions (default: transform).
- ``--transform-setup / --no-transform-setup``: Convert setUp/tearDown methods to pytest fixtures (default: transform).
- ``--transform-subtests / --no-transform-subtests``: Convert subTest loops to pytest.mark.parametrize (default: transform).
- ``--transform-skips / --no-transform-skips``: Convert unittest skip decorators to pytest skip decorators (default: transform).
- ``--transform-imports / --no-transform-imports``: Transform unittest imports to pytest imports (default: transform).

## Processing and Performance
- ``--continue-on-error``: Continue processing when individual files fail (useful for large codebases) (presence-only flag).
- ``--max-concurrent N``: Maximum files to process concurrently (1-50, default: 1). Note: Concurrent file processing is not currently supported and this flag is reserved for future implementation.
- ``--cache-analysis / --no-cache-analysis``: Cache analysis results for better performance on repeated runs (default: cache).

## Analysis and Discovery
- ``--prefix PREFIX``: Allowed test method prefixes; repeatable (default: ``test``, ``spec``, ``should``, ``it``). Supports custom prefixes like ``spec``, ``should``, ``it`` for modern testing frameworks.
- ``--detect-prefixes``: Auto-detect test method prefixes from source files (presence-only flag).
- ``--assert-places N``: Default decimal places for assertAlmostEqual transformations (1-15, default: 7).
- ``--max-file-size N``: Maximum file size in MB to process (1-100, default: 10).

## Logging and Output
- ``-v, --verbose``: Verbose logging (presence-only flag).
- ``--info``: Enable info logging output (presence-only flag).
- ``--debug``: Enable debug logging output (presence-only flag).
- ``--log-level LEVEL``: Set logging level (DEBUG, INFO, WARNING, ERROR) (default: INFO).

## Dry-run and Preview
- ``--dry-run``: Do not write files; return or display generated output (presence-only flag).
  - With ``--dry-run --diff``: show unified diffs (``--diff`` is presence-only).
  - With ``--dry-run --list``: list files only (``--list`` is presence-only).
- ``--diff``: Show unified diffs in dry-run mode (presence-only flag).
- ``--list``: List files only in dry-run mode (presence-only flag).
- ``--posix``: Format displayed file paths using POSIX separators when True (presence-only flag).

## Error Handling
- ``--fail-fast``: Stop on first error (presence-only flag).

## Reporting
- ``--report``: Generate a migration report (presence-only flag).
- ``--report-format [json|html|markdown]``: Report format (default: json).

## Configuration Files
- ``-c, --config FILE``: YAML configuration file to load settings from (overrides CLI defaults).

## Advanced Options
- ``--source-map``: Create source mapping for debugging transformations (advanced users) (presence-only flag).
- ``--max-depth``: Maximum depth to traverse nested control flow structures (3-15, default: 7). Controls how deeply the transformer explores nested control flow blocks (try/except/else/finally, with, if/else, for/else, while/else) when processing assertions.

## Enhanced Validation Features
- ``--suggestions``: Show intelligent configuration suggestions (presence-only flag).
- ``--use-case-analysis``: Show detected use case analysis (presence-only flag).
- ``--field-help FIELD``: Show help for a specific configuration field.
- ``--list-templates``: List available configuration templates (presence-only flag).
- ``--template TEMPLATE``: Use a pre-configured template (e.g., 'basic_migration', 'ci_integration').
- ``--generate-docs [markdown|html]``: Generate configuration documentation.
- ``generate-templates``: Generate configuration template files for all use cases (standalone command).


YAML Configuration File Format
-------------------------------

You can use a YAML configuration file to store migration settings and avoid specifying them on the command line each time. Use the ``--config`` or ``-c`` flag to specify the configuration file path.

### Configuration File Structure

The YAML configuration file supports all CLI options with their corresponding parameter names. Here's a comprehensive example:

```yaml
# File Discovery and Input
target_root: /path/to/output/directory
root_directory: /path/to/source/directory
file_patterns:
  - "test_*.py"
  - "spec_*.py"
recurse_directories: true

# Output and File Handling
backup_originals: true
backup_root: /path/to/backup/directory
target_suffix: "_migrated"
target_extension: ".py"
preserve_file_encoding: true

# Formatting and Code Quality
line_length: 120
format_output: true

# Import Handling
remove_unused_imports: true
preserve_import_comments: true

# Transform Selection (all enabled by default)
transform_assertions: true
transform_setup_teardown: true
transform_subtests: true
transform_skip_decorators: true
transform_imports: true

# Processing and Performance
continue_on_error: false
max_concurrent_files: 1  # Note: Concurrent processing not currently supported
cache_analysis_results: true

# Analysis and Discovery
test_method_prefixes:
  - "test"
  - "spec"
  - "should"
  - "it"
assert_almost_equal_places: 7
max_file_size_mb: 10

# Logging and Output
log_level: "INFO"
verbose: false

# Error Handling
fail_fast: false

# Reporting
generate_report: true
report_format: "json"

# Advanced Options
create_source_map: false
max_depth: 7

# Intelligent Configuration System
intelligent_suggestions: false
use_case_analysis: false
field_help: null  # Set to a field name to get help (e.g., "max_file_size_mb")
list_available_templates: false
configuration_template: null  # Set to template name (e.g., "ci_integration")
generate_config_docs: null  # Set to "markdown" or "html" to generate docs

# Enhanced Validation and Error Recovery
enable_smart_error_recovery: true
error_recovery_strategies:
  - "suggest_alternatives"
  - "provide_examples"
  - "validate_dependencies"
comprehensive_field_metadata: true
interactive_config_builder: false
```

### Configuration File Usage

Create a configuration file (e.g., `migrate-config.yaml`):

```bash
# Generate a default configuration file
python -m splurge_unittest_to_pytest.cli init-config migrate-config.yaml

# Use the configuration file
python -m splurge_unittest_to_pytest.cli migrate --config migrate-config.yaml tests/

# Override specific settings from the config file
python -m splurge_unittest_to_pytest.cli migrate --config migrate-config.yaml --dry-run tests/
```

### Configuration Precedence

Settings are applied in this order of precedence (highest to lowest):

1. **CLI flags**: Command-line arguments override all other settings
2. **YAML configuration file**: Settings from the `--config` file
3. **Default values**: Built-in defaults for any unspecified options

This allows you to:
- Store common settings in a configuration file
- Override specific settings for one-off runs using CLI flags
- Share configuration files across team members or CI/CD pipelines

Examples
--------

Preview a single file (print converted code):

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/test_example.py --dry-run
```

Show unified diffs for a directory:

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/ -r --dry-run --diff
```

Write changes to a target directory (formatting always applied). Backups are created by default; to disable backups pass ``--skip-backup``:

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/ -r -t converted
# To disable backups when writing:
python -m splurge_unittest_to_pytest.cli migrate tests/ -r -t converted --skip-backup
```

Redirect backups to a custom directory while preserving folder structure:

```bash
# Create backups in a centralized location when processing multiple directories:
python -m splurge_unittest_to_pytest.cli migrate tests/ -r --backup-root ./backups
```

Override extension (write `.txt` files instead of `.py`):

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/test_example.py --ext txt
```

Migrate with custom test prefixes for modern testing frameworks:

```bash
# Support spec_ methods for BDD-style tests
python -m splurge_unittest_to_pytest.cli migrate tests/ --prefix spec --dry-run

# Support multiple prefixes for hybrid test suites
python -m splurge_unittest_to_pytest.cli migrate tests/ --prefix test --prefix spec --prefix should
```

Migrate with nested test class support:

```bash
# Automatically handles nested test classes
python -m splurge_unittest_to_pytest.cli migrate tests/ --dry-run --diff
```

Use YAML configuration files:

```bash
# Generate a default configuration file
python -m splurge_unittest_to_pytest.cli init-config my-config.yaml

# Migrate using a configuration file
python -m splurge_unittest_to_pytest.cli migrate --config my-config.yaml tests/

# Override specific settings from config file with CLI flags
python -m splurge_unittest_to_pytest.cli migrate --config my-config.yaml --dry-run --no-transform-assertions tests/
```

## Intelligent Configuration System

Get intelligent suggestions for your project:

```bash
# Analyze project and show configuration suggestions
python -m splurge_unittest_to_pytest.cli migrate tests/ --suggestions

# Get comprehensive use case analysis
python -m splurge_unittest_to_pytest.cli migrate tests/ --use-case-analysis

# Combine suggestions with analysis
python -m splurge_unittest_to_pytest.cli migrate tests/ --suggestions --use-case-analysis
```

Use configuration templates:

```bash
# List all available templates
python -m splurge_unittest_to_pytest.cli migrate --list-templates

# Use a specific template for CI/CD integration
python -m splurge_unittest_to_pytest.cli migrate tests/ --template ci_integration

# Use template for large codebase migration
python -m splurge_unittest_to_pytest.cli migrate tests/ --template large_codebase
```

Get help and documentation:

```bash
# Get detailed help for a configuration field
python -m splurge_unittest_to_pytest.cli migrate --field-help max_file_size_mb

# Generate markdown documentation for all configuration options
python -m splurge_unittest_to_pytest.cli migrate --generate-docs markdown

# Generate HTML documentation
python -m splurge_unittest_to_pytest.cli migrate --generate-docs html
```

Interactive configuration:

```bash
# Create configuration interactively (guided setup)
python -m splurge_unittest_to_pytest.cli init-config --interactive my-project-config.yaml
```

## Enhanced Validation Features

Analyze configuration and get intelligent suggestions:

```bash
# Show detected use case and configuration suggestions
python -m splurge_unittest_to_pytest.cli migrate tests/ --suggestions --use-case-analysis

# Get help for a specific configuration field
python -m splurge_unittest_to_pytest.cli migrate --field-help target_root

# List available configuration templates
python -m splurge_unittest_to_pytest.cli migrate --list-templates

# Use a template for migration
python -m splurge_unittest_to_pytest.cli migrate tests/ --template ci_integration

# Generate configuration documentation
python -m splurge_unittest_to_pytest.cli migrate --generate-docs markdown
```
python -m splurge_unittest_to_pytest.cli generate-templates --output-dir ./my-templates --format json

# Error Recovery and Analysis
python -m splurge_unittest_to_pytest.cli error-recovery --error "File not found: /missing/file.py"
python -m splurge_unittest_to_pytest.cli error-recovery --error "Permission denied" --interactive
python -m splurge_unittest_to_pytest.cli error-recovery --error "Invalid config" --category configuration --workflow-only

# Interactive Configuration Building
python -m splurge_unittest_to_pytest.cli configure
python -m splurge_unittest_to_pytest.cli configure --output-file config.yaml
python -m splurge_unittest_to_pytest.cli configure --analyze-only
```

Selectively disable specific transformations:

```bash
# Keep unittest assertions unchanged but convert everything else
python -m splurge_unittest_to_pytest.cli migrate --no-transform-assertions tests/

# Convert only assertions and imports, skip setup/teardown conversion
python -m splurge_unittest_to_pytest.cli migrate --transform-assertions --transform-imports --no-transform-setup tests/

# Continue processing even if some files fail
python -m splurge_unittest_to_pytest.cli migrate --continue-on-error tests/
```

Control output formatting and imports:

```bash
# Skip code formatting (faster but may produce inconsistent style)
python -m splurge_unittest_to_pytest.cli migrate --no-format tests/

# Keep unused unittest imports (may leave redundant imports)
python -m splurge_unittest_to_pytest.cli migrate --no-remove-imports tests/

# Preserve comments in import sections
python -m splurge_unittest_to_pytest.cli migrate --preserve-import-comments tests/
```

Advanced analysis and discovery:

```bash
# Auto-detect test method prefixes from source files
python -m splurge_unittest_to_pytest.cli migrate --detect-prefixes tests/

# Support multiple custom test prefixes
python -m splurge_unittest_to_pytest.cli migrate --prefix test --prefix spec --prefix should --prefix it tests/

# Set precision for floating-point assertions
python -m splurge_unittest_to_pytest.cli migrate --assert-places 10 tests/
```

Programmatic API
-----------------

Use :func:`splurge_unittest_to_pytest.main.migrate` for programmatic migration:

```python
from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.context import MigrationConfig

config = MigrationConfig(dry_run=True)
result = main.migrate(["tests/test_example.py"], config=config)
if result.is_success():
		gen_map = result.metadata.get("generated_code", {})
		print(gen_map)
else:
		print("Migration failed:", result.error)
```

The function returns a :class:`Result` that contains migrated paths and
optional metadata. When ``dry_run`` is enabled the result metadata often
includes a ``generated_code`` mapping of target paths to code strings.

Example: configure migration programmatically

```python
from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.context import MigrationConfig

config = MigrationConfig(
    dry_run=True,
    enable_decision_analysis=True,  # Multi-pass analyzer is always enabled
)
result = main.migrate(["tests/test_example.py"], config=config)
if result.is_success():
	gen_map = result.metadata.get("generated_code", {})
	print(gen_map)
else:
	print("Migration failed:", result.error)
```

Programmatic helper: `prepare_config`
------------------------------------

Use `prepare_config` when you want a single entrypoint to build a
`MigrationConfig` programmatically. It applies defaults, supports an
optional interactive flow, and attempts to run enhanced validation. The
function always returns a `MigrationConfig` instance for consistent use in
tests and programmatic calls.

```python
from splurge_unittest_to_pytest import prepare_config

cfg = prepare_config(interactive=False, questions=[{"key": "line_length", "default": 88}])
print(cfg.line_length)  # -> 88
```

Safety and limitations
----------------------

- The tool targets common and idiomatic ``unittest`` patterns. Highly
	dynamic code, metaprogramming, or uncommon testing patterns may not be
	fully convertible automatically.
- Always inspect conversions (use ``--dry-run --diff``) and run your
	project tests after migration. The tool aims to be conservative and
	preserve behavior, but automated transformations require manual
	verification in complex cases.

Enhanced robustness and reliability
----------------------------------

The tool includes comprehensive error handling, cross-platform path support,
and intelligent fallback mechanisms:

- **Cross-platform compatibility**: Enhanced Windows path handling with length validation (260 char limit) and invalid character detection
- **Robust configuration validation**: Improved error messages with specific guidance for fixing configuration issues
- **Graceful error handling**: Comprehensive fallback mechanisms prevent tool failures on edge cases
- **Deprecated API support**: Handles legacy unittest method names (`assertAlmostEquals`, `assertNotAlmostEquals`) for maximum compatibility
- **Intelligent transformation**: Complex transformation logic broken into focused, maintainable functions with enhanced error reporting

Advanced Error Reporting and Recovery
------------------------------------

The tool now includes a sophisticated error reporting system that provides intelligent guidance for resolving issues:

- **Smart Error Classification**: Automatically categorizes errors into 10 categories (CONFIGURATION, FILESYSTEM, PARSING, TRANSFORMATION, VALIDATION, PERMISSION, DEPENDENCY, NETWORK, RESOURCE, UNKNOWN)
- **Context-Aware Suggestions**: Generates intelligent suggestions based on error type and context, with priority-based sorting
- **Recovery Workflows**: Provides step-by-step recovery guidance for common error scenarios with estimated completion times and success rates
- **Interactive Error Recovery**: New CLI command `error-recovery` offers guided assistance for error resolution

Error Recovery Example:

```bash
# Analyze an error and get recovery suggestions
splurge-unittest-to-pytest error-recovery \
  --error "File not found: /missing/file.py" \
  --category filesystem

# Interactive recovery mode
splurge-unittest-to-pytest error-recovery \
  --error "Permission denied" \
  --interactive
```

Programmatic Error Reporting:

```python
from splurge_unittest_to_pytest.error_reporting import ErrorReporter

reporter = ErrorReporter()
error = ValueError("Configuration error: target_root does not exist")
report = reporter.report_error(error, {"target_root": "/missing/path"})

# Access enhanced error information
print(f"Category: {report['error']['category']}")
print(f"Severity: {report['error']['severity']}")
print(f"Suggestions: {len(report['error']['suggestions'])}")
print(f"Recovery workflow: {report['recovery_workflow']['title']}")
```

Interactive Configuration Building
---------------------------------

The tool now includes an intelligent configuration builder that analyzes your project and guides you through creating optimal configurations:

- **Project Analysis**: Automatically detects project type, test patterns, and complexity
- **Interactive Workflows**: Different configuration experiences based on detected project types
- **Intelligent Defaults**: Suggests appropriate settings based on project analysis
- **Configuration Validation**: Validates and enhances configurations before use

Configuration Building Example:

```bash
# Analyze project and create configuration interactively
python -m splurge_unittest_to_pytest.cli configure

# Save configuration to file
python -m splurge_unittest_to_pytest.cli configure --output-file my-config.yaml

# Just analyze project without creating configuration
python -m splurge_unittest_to_pytest.cli configure --analyze-only
```

Programmatic Configuration Building:

```python
from splurge_unittest_to_pytest.config_validation import InteractiveConfigBuilder

builder = InteractiveConfigBuilder()
config = builder.build_configuration_interactive()

# Use the validated configuration
from splurge_unittest_to_pytest import main
result = main.migrate(["tests/"], config=config)
```

Note on top-level __main__ guards and runtime test invocations
------------------------------------------------------------

- The transformer removes top-level ``if __name__ == "__main__":`` guard
	blocks and any top-level calls to ``unittest.main()`` or ``pytest.main()``.
	This avoids emitting runtime test-invocation code in transformed files.
	The expectation is that tests are executed via the command line or a
	test runner (for example, ``pytest``). If you need to preserve these
	guards for runnable transformed files, please open an issue or feature
	request — there is no preservation option in the current release.

Developer notes
---------------

- Tests: run ``python -m pytest -q`` to execute the full test suite.
- Formatting / linting: use ``python -m ruff check --fix`` and
	``python -m ruff format``.
- Architecture: the pipeline is organized as Jobs → Tasks → Steps, each
	with a single responsibility. See the source under ``splurge_unittest_to_pytest/`` for
	concrete implementations.
- Assertion transformer helpers: ``assert_transformer.py`` now exposes
	plain functions such as ``_rewrite_expression`` and
	``_rewrite_unary_operation`` backed by a metadata-aware
	``parenthesized_expression`` helper. Focused tests in
	``tests/unit/test_assert_transformer_expression_rewrites.py`` cover
	positive, negative, and edge-case flows for these helpers.
- Contributions: open a PR against the ``main`` branch and include tests
	for new behavior. Keep changes small and run the full suite before
	requesting review.

- Static type-checking notes: we apply a targeted mypy override to exclude
	the runtime CLI module (`splurge_unittest_to_pytest.cli`) from strict
	checks. This keeps the library modules under tight static scrutiny while
	avoiding false-positives caused by Typer's runtime OptionInfo objects.
	See `docs/developer/mypy-overrides.md` for details and instructions to
	re-enable strict checking for the CLI module during reviews.

Recent updates
--------------

- **Enhanced pattern support** (October 2025): Comprehensive support for modern testing patterns:
  - **Custom test prefixes**: Configurable support for `spec_`, `should_`, `it_` and other prefixes beyond `test_`
  - **Nested test classes**: Proper handling of test classes nested within other test classes
  - **Advanced setup method detection**: Recognition of various setup method naming patterns (`setup_method`, `before_each`, `cleanup`, etc.)
  - **Enhanced exception handling**: Improved support for custom exception types, exception chaining, and advanced warning assertions
- **Multi-pass analyzer integration**: Implemented a sophisticated 5-pass analysis pipeline that intelligently determines transformation strategies for `subTest` loops, preserving semantics where code mutates accumulators or depends on loop ordering.
- The decision model is now always enabled for improved transformation accuracy and consistency.
- Expanded unit tests for assertion rewriting and string-fallbacks in the assert transformer.
