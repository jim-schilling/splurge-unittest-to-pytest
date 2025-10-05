
# splurge-unittest-to-pytest


[![PyPI](https://img.shields.io/pypi/v/splurge-unittest-to-pytest.svg)](https://pypi.org/project/splurge-unittest-to-pytest)
[![Development Status](https://img.shields.io/badge/Development%20Status-Alpha-lightgrey.svg)](#)

[![CI (py3.13)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci-py313.yml/badge.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions)
[![ruff](https://img.shields.io/badge/ruff-passing-brightgreen.svg)](https://github.com/charliermarsh/ruff)
[![mypy](https://img.shields.io/badge/mypy-passing-brightgreen.svg)](https://github.com/python/mypy)

A practical toolset to migrate Python unittest-based tests into idiomatic
pytest style. The project features a **multi-pass analyzer** that intelligently
analyzes test patterns and applies transformations with high confidence.
The project exposes both a command-line interface and a programmatic API
built around libcst-based transformations to preserve semantics while
producing readable pytest code.

**Enhanced robustness**: Comprehensive error handling, cross-platform path support,
and intelligent fallback mechanisms ensure reliable operation across diverse
codebases and environments.

## Quick start

Install (recommended using a virtual environment):

```bash
pip install splurge-unittest-to-pytest
```

Run the CLI (module mode shown):

```bash
python -m splurge_unittest_to_pytest migrate [OPTIONS] [SOURCE_FILES...]
 OR
splurge-unittest-to-pytest migrate [OPTIONS] [SOURCE_FILES...]
```

By default the tool preserves the original source file extensions and will
write converted output next to the inputs. Use ``-t/--target-root`` to write to
an alternate location.

## At-a-glance features

- **Multi-pass analyzer** that intelligently analyzes test patterns and applies
  transformations with high confidence, preserving semantics where code mutates
  accumulators or depends on loop ordering.
- **Enhanced pattern support**: Custom test prefixes (``spec_``, ``should_``, ``it_``),
  nested test classes, custom setup methods, and advanced exception handling.
- **Intelligent Configuration System**: Advanced validation with cross-field rules,
  use case detection, and intelligent suggestions for optimal settings.
- **Smart Error Recovery**: Context-aware error classification, actionable suggestions,
  and step-by-step recovery workflows for complex migration scenarios.
- **Configuration Templates**: Pre-configured templates for common scenarios
  (basic migration, CI/CD integration, batch processing, advanced analysis).
- **Interactive Configuration Builder**: Guided configuration process with
  intelligent defaults based on project analysis.
- **Comprehensive Documentation**: Auto-generated configuration documentation
  with examples, constraints, and common mistakes for all 30+ settings.
- Safe CST-based transformations using `libcst` to preserve formatting and
  minimize behavior changes.
- Dry-run preview modes: print converted code, show unified diffs
  (``--diff``), or list files only (``--list``).
- Always applies code formatters: ``isort`` + ``black``.
- Conservative transformations: class-based tests inheriting from
  ``unittest.TestCase`` are preserved to maintain class-scoped fixtures and
  organization unless a conversion is explicitly desired.
- Backups of originals are created by default; pass ``--skip-backup`` to disable creating backup copies before writing. Note: if a ``.backup`` file already exists it will be preserved and not overwritten.
- **Configurable discovery patterns**: Custom test method prefixes (``--prefix``),
  nested class support, and enhanced setup method detection via the CLI or
  a programmatic ``MigrationConfig``.

See `docs/README-DETAILS.md` for a comprehensive feature and CLI reference.

Programmatic API and developer docs

For programmatic usage, templates, and end-to-end examples see the API docs:

- `docs/api/README.md` — programmatic API index with examples and workflows
- `docs/api/programmatic_api.md` — migrate() usage and EventBus example
- `docs/api/configuration_api.md` — configuration schema, templates, and validation notes
- `docs/api/cli_mapping.md` — CLI to programmatic mapping and CI example
- `docs/api/end_to_end_workflow.md` — a complete end-to-end programmatic workflow
- `docs/configuration/configuration-reference.md` — full configuration reference (auto-generated)

## Common CLI options (summary)

- ``-d, --dir DIR``: Root directory for discovery
- ``-f, --file PATTERN``: Glob pattern(s) to select files (repeatable)
 - ``--dry-run``: Preview generated output without writing files (presence-only flag)
 - ``--diff``: When used with ``--dry-run``, show unified diffs (presence-only flag)
 - ``--list``: When used with ``--dry-run``, list files only (presence-only flag)
 - ``--posix``: Force POSIX-style path output in dry-run mode (presence-only flag)
 - (no ``--quiet`` flag) The tool is quiet by default; use ``--verbose``/``--debug`` to increase output verbosity.
 - ``--suffix SUFFIX``: Append a suffix to converted filenames
- ``--backup-root DIR``: Root directory for backup files when recursing. When specified, backups preserve folder structure. By default, backups are created next to the original files.
- ``--skip-backup``: Skip creating backup copies of originals when writing (presence-only flag). By default the tool will create a backup of the original file when writing; if a backup file already exists the tool will not overwrite it—an existing ``.backup`` file is preserved.
- ``--prefix PREFIX``: Allowed test method prefixes (repeatable; default: ``test``).
  Supports custom prefixes like ``spec``, ``should``, ``it`` for modern testing frameworks.
- ``-c, --config FILE``: YAML configuration file to load settings from (overrides CLI defaults).
- ``--suggestions``: Show intelligent configuration suggestions (presence-only flag).
- ``--use-case-analysis``: Show detected use case analysis (presence-only flag).
- ``--field-help FIELD``: Show help for a specific configuration field.
- ``--list-templates``: List available configuration templates (presence-only flag).
- ``--template TEMPLATE``: Use a pre-configured template (e.g., 'basic_migration', 'ci_integration').
- ``--generate-docs [markdown|html]``: Generate configuration documentation.

For the full set of flags and detailed help, run:

```bash
python -m splurge_unittest_to_pytest migrate --help
```

## Examples

Preview conversion for a single file and print generated code:

```bash
python -m splurge_unittest_to_pytest migrate --dry-run tests/test_example.py
```

Show unified diff for a directory:

```bash
python -m splurge_unittest_to_pytest migrate -d tests --dry-run --diff
```

Verbose dry-run with POSIX paths:

The tool is quiet by default. Use ``--verbose`` or ``--debug`` or ``--info`` to increase output verbosity. For example:

```bash
python -m splurge_unittest_to_pytest migrate -d tests --dry-run --posix --verbose
```

Perform migration and write files to `converted/` (preserve extensions). Backups are created by default; to disable backups pass ``--skip-backup``:

```bash
python -m splurge_unittest_to_pytest migrate -d tests -t converted
# Disable backups when writing:
python -m splurge_unittest_to_pytest migrate -d tests -t converted --skip-backup
```

Redirect backups to a custom directory while preserving folder structure:

```bash
# Create backups in a centralized location when processing multiple directories:
python -m splurge_unittest_to_pytest migrate -d tests --backup-root ./backups
```

Migrate with custom test prefixes for modern testing frameworks:

```bash
# Support spec_ methods for BDD-style tests
python -m splurge_unittest_to_pytest migrate tests/ --prefix spec --dry-run

# Support multiple prefixes for hybrid test suites
python -m splurge_unittest_to_pytest migrate tests/ --prefix test --prefix spec --prefix should
```

Use intelligent configuration suggestions and analysis:

```bash
# Get intelligent suggestions for your project
python -m splurge_unittest_to_pytest migrate tests/ --suggestions

# Analyze your project's use case and get tailored recommendations
python -m splurge_unittest_to_pytest migrate tests/ --use-case-analysis

# Get help for a specific configuration field
python -m splurge_unittest_to_pytest migrate --field-help max_file_size_mb
```

Use configuration templates for common scenarios:

```bash
# List available templates
python -m splurge_unittest_to_pytest migrate --list-templates

# Use a pre-configured template
python -m splurge_unittest_to_pytest migrate tests/ --template ci_integration

# Generate configuration documentation
python -m splurge_unittest_to_pytest migrate --generate-docs markdown
```

Use YAML configuration files for complex setups:

```bash
# Create a configuration file with all settings
python -m splurge_unittest_to_pytest init-config my-migration.yaml

# Use the configuration file
python -m splurge_unittest_to_pytest migrate --config my-migration.yaml tests/
```

## Programmatic usage (quick)

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

## Contributing & development

- Run tests locally: ``python -m pytest -q``
- Use ruff for linting/formatting: ``python -m ruff check --fix`` and
  ``python -m ruff format``
- Tests exercise the core transformers and pipeline; run the full suite
  before opening PRs.

See `docs/README-DETAILS.md` for developer notes, architecture guidance, and
contribution conventions.

## License

MIT. See `LICENSE` for details.
