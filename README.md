# splurge-unittest-to-pytest

A tool to migrate Python unittest suites to pytest.

## CLI Usage

```bash
splt migrate [OPTIONS] [SOURCE_FILES...]
# Alternatively via module:
python -m splurge_unittest_to_pytest.cli migrate [OPTIONS] [SOURCE_FILES...]
```

### Key Options

- -d, --dir DIR: Root directory for input discovery.
- -f, --file PATTERN: Glob pattern(s) to select files. Repeatable. Defaults to `test_*.py`.
- -r, --recurse / --no-recurse: Recurse directories (default: recurse).
- -t, --target-dir DIR: Directory to write outputs.
- --preserve-structure / --no-preserve-structure: Keep original directory structure (default: preserve).
- --backup / --no-backup: Create `.backup` of originals (default: backup).
- --convert-classes / --no-convert-classes: Convert TestCase classes to functions (default: on).
- --merge-setup / --no-merge-setup: Merge setUp/tearDown into pytest fixtures (default: on).
- --fixtures / --no-fixtures: Generate pytest fixtures (default: on).
- --fixture-scope [function|class|module|session]: Scope for generated fixtures (default: function).
- --format / --no-format: Apply black/isort formatting (default: on).
- --optimize-imports / --no-optimize-imports (default: on).
- --type-hints / --no-type-hints: Add basic type hints (default: off).
- --line-length N: Max line length for formatting (default: 120).
- --dry-run: Do not write files, just report (default: off).
- --fail-fast: Stop on first error (default: off).
- --parallel / --no-parallel: Process files in parallel (default: on).
- --workers N: Max worker processes (default: 4).
- -v, --verbose: Verbose logging (default: off).
- --report / --no-report: Generate migration report (default: on).
- --report-format [json|html|markdown]: Report format (default: json).
- --config FILE: Load configuration from YAML.
- --prefix PREFIX: Allowed test method prefixes; repeatable (default: `test`).

### Examples

```bash
# Migrate tests in a directory, using default pattern (test_*.py)
python -m splurge_unittest_to_pytest.cli migrate -d tests

# Migrate recursively with multiple patterns
python -m splurge_unittest_to_pytest.cli migrate -d src -f "test_*.py" -f "*_spec.py" -r

# Restrict to methods starting with `test` or `given`
python -m splurge_unittest_to_pytest.cli migrate -d tests --prefix test --prefix given

# Output to a separate directory and disable formatting
python -m splurge_unittest_to_pytest.cli migrate -d tests -t converted --no-format
```
