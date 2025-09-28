
# splurge-unittest-to-pytest

[![Version](https://img.shields.io/badge/version-2025.0.0-blue.svg)](https://pypi.org/project/splurge-unittest-to-pytest)
[![PyPI](https://img.shields.io/pypi/v/splurge-unittest-to-pytest.svg)](https://pypi.org/project/splurge-unittest-to-pytest)
[![CI](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions/workflows/ci.yml/badge.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest/actions)
[![ruff](https://img.shields.io/badge/ruff-passing-brightgreen.svg)](https://github.com/charliermarsh/ruff)
[![mypy](https://img.shields.io/badge/mypy-passing-brightgreen.svg)](https://github.com/python/mypy)

A small, practical tool to migrate Python unittest-based tests into pytest style.

This repo contains a CLI and a set of libcst-based transformers that perform safe,
opinionated migrations from unittest.TestCase code to pytest-style tests.

## Quick start

Run the CLI (module mode shown):

python -m splurge_unittest_to_pytest.cli migrate [OPTIONS] [SOURCE_FILES...]

By default the tool preserves the original source file extensions and will write
converted output next to the inputs (or into a target directory when provided).

## Notable features

- Dry-run preview: use `--dry-run` to see generated conversions without writing
	files. Presentation modes are available: default prints converted code,
	`--diff` shows a unified diff, and `--list` prints headers only.
- File paths are displayed using native OS separators by default. Use `--posix`
	to force POSIX-style paths in dry-run output. `--quiet` suppresses informational
	headers.
- Transformer-level import cleanup: removal of unused `unittest` imports is
	handled in the transformer stage (not the formatter), and dynamic import
	patterns (e.g. `__import__`, `import_module`) are detected and treated as
	usages to avoid removing needed imports.
- No legacy fallback naming: the CLI no longer emits files with a
	`.pytest.py` fallback by default; original extensions are preserved unless
	overridden with `--ext` or `--suffix`.

## Common options (high level)

- `-d, --dir DIR` : directory root for discovery
- `-f, --file PATTERN` : glob pattern(s) to select files (repeatable)
- `-r, --recurse/--no-recurse` : recurse directories (default: recurse)
- `-t, --target-dir DIR` : directory to write converted files
- `--dry-run` : preview generated files without writing
- `--diff` : when used with `--dry-run`, show unified diffs
- `--list` : when used with `--dry-run`, list headers only
- `--posix` : force POSIX-style path output in dry-run mode
- `--quiet` : suppress dry-run headers and extra information
- `--ext EXT` : set the file extension for written files (overrides original)
- `--suffix SUFFIX` : append a suffix to converted filenames
- Formatting: generated code is always formatted with `black` and `isort`.

- Preservation of TestCase class structure: when a class in the source
	inherits from `unittest.TestCase`, the tool preserves the class-based
	structure (methods remain on the class) rather than converting the class
	into free functions. This helps keep test organization and fixtures that
	rely on class-level state intact.
- `--backup/--no-backup` : keep backup copies of originals
- `--prefix` : allowed test method prefixes (repeatable, default `test`)

See `python -m splurge_unittest_to_pytest.cli migrate --help` for a full list
of flags and their detailed descriptions.

## Examples

# Preview conversion for a single file and print the generated code
python -m splurge_unittest_to_pytest.cli migrate --dry-run tests/test_example.py

# Show unified diff for a whole directory
python -m splurge_unittest_to_pytest.cli migrate -d tests --dry-run --diff

# Quiet dry-run that prints POSIX paths
python -m splurge_unittest_to_pytest.cli migrate -d tests --dry-run --posix --quiet

# Perform migration and write files to `converted/`, preserving extensions
python -m splurge_unittest_to_pytest.cli migrate -d tests -t converted

## Documentation & changelog

See `docs/README-DETAILS.md` for a deeper description of the transformation
phases, transformer design, and extension points. The `CHANGELOG.md` contains
recent changes and migration notes.

## Contributing

Contributions, bug reports, and PRs are welcome. Please run the test suite and
formatters before opening a PR. See `docs/README-DETAILS.md` for development
notes and repository conventions.

## License

MIT. See `LICENSE` for details.
