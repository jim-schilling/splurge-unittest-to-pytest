
# splurge-unittest-to-pytest

[![Version](https://img.shields.io/badge/version-2025.0.0-blue.svg)](https://pypi.org/project/splurge-unittest-to-pytest)
[![PyPI](https://img.shields.io/pypi/v/splurge-unittest-to-pytest.svg)](https://pypi.org/project/splurge-unittest-to-pytest)
[![Development Status](https://img.shields.io/badge/Development%20Status-Alpha-lightgrey.svg)](#)

[![CI (py3.13)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci-py313.yml/badge.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions)
[![ruff](https://img.shields.io/badge/ruff-passing-brightgreen.svg)](https://github.com/charliermarsh/ruff)
[![mypy](https://img.shields.io/badge/mypy-passing-brightgreen.svg)](https://github.com/python/mypy)

A practical toolset to migrate Python unittest-based tests into idiomatic
pytest style. The project exposes both a command-line interface and a
programmatic API built around libcst-based transformations to preserve
semantics while producing readable pytest code.

## Quick start

Install (recommended using a virtual environment):

```bash
pip install splurge-unittest-to-pytest
```

Run the CLI (module mode shown):

```bash
python -m splurge_unittest_to_pytest.cli migrate [OPTIONS] [SOURCE_FILES...]
 OR
splurge-unittest-to-pytest migrate [OPTIONS] [SOURCE_FILES...]
```

By default the tool preserves the original source file extensions and will
write converted output next to the inputs. Use ``-t/--target-dir`` to write to
an alternate location.

## At-a-glance features

- Safe CST-based transformations using `libcst` to preserve formatting and
  minimize behavior changes.
- Dry-run preview modes: print converted code, show unified diffs
  (``--diff``), or list files only (``--list``).
- Always applies code formatters: ``isort`` + ``black``.
- Conservative transformations: class-based tests inheriting from
  ``unittest.TestCase`` are preserved to maintain class-scoped fixtures and
  organization unless a conversion is explicitly desired.
 - Backups of originals are created by default; pass ``--skip-backup`` to disable creating backup copies before writing. Note: if a ``.backup`` file already exists it will be preserved and not overwritten.
- Configurable discovery patterns, test method prefixes, and other options
  via the CLI or a programmatic ``MigrationConfig``.

See `docs/README-DETAILS.md` for a comprehensive feature and CLI reference.

## Common CLI options (summary)

- ``-d, --dir DIR``: Root directory for discovery
- ``-f, --file PATTERN``: Glob pattern(s) to select files (repeatable)
 - ``--dry-run``: Preview generated output without writing files (presence-only flag)
 - ``--diff``: When used with ``--dry-run``, show unified diffs (presence-only flag)
 - ``--list``: When used with ``--dry-run``, list files only (presence-only flag)
 - ``--posix``: Force POSIX-style path output in dry-run mode (presence-only flag)
 - ``--quiet``: Suppress extras in dry-run output (presence-only flag)
 - ``--suffix SUFFIX``: Append a suffix to converted filenames
 - ``--skip-backup``: Skip creating backup copies of originals when writing (presence-only flag). By default the tool will create a backup of the original file when writing; if a backup file already exists the tool will not overwrite it—an existing ``.backup`` file is preserved.
 - ``--suffix SUFFIX``: Append a suffix to converted filenames
 - ``--backup``: Create backup copies of originals when writing (presence-only flag; default: off)
- ``--prefix PREFIX``: Allowed test method prefixes (repeatable; default: ``test``)

For the full set of flags and detailed help, run:

```bash
splurge-unittest-to-pytest migrate --help
```

## Examples

Preview conversion for a single file and print generated code:

```bash
splurge-unittest-to-pytest migrate --dry-run tests/test_example.py
```

Show unified diff for a directory:

```bash
python -m splurge_unittest_to_pytest.cli migrate -d tests --dry-run --diff
```

Quiet dry-run with POSIX paths:

```bash
python -m splurge_unittest_to_pytest.cli migrate -d tests --dry-run --posix --quiet
```

Perform migration and write files to `converted/` (preserve extensions). Backups are created by default; to disable backups pass ``--skip-backup``:

```bash
python -m splurge_unittest_to_pytest.cli migrate -d tests -t converted
# Disable backups when writing:
python -m splurge_unittest_to_pytest.cli migrate -d tests -t converted --skip-backup
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
