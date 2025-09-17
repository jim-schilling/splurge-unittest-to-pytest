"""Command line interface for splurge-unittest-to-pytest.

Provides the Click-based ``main`` console command used to convert
unittest-style tests to pytest-style tests from the command line.

This module parses CLI options (for example, ``--setup-methods``,
``--teardown-methods``, ``--test-methods``, ``--dry-run``, and
``--output``) and forwards them to the conversion helpers in
``splurge_unittest_to_pytest.main`` and the converter package. The
command supports dry-run mode and optional backup/output directory
behaviour.

Publics:
    main: Click entry point suitable for use as a console script.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

import sys
from pathlib import Path

import click
import logging
import os

from . import __version__
from .exceptions import (
    EncodingError,
    FileNotFoundError as SplurgeFileNotFoundError,
    ParseError,
    PermissionDeniedError,
    SplurgeError,
)
from .main import convert_file, find_unittest_files, ConversionResult, PatternConfigurator
from .converter.helpers import parse_method_patterns

DOMAINS = ["cli"]

# If diagnostics are enabled, wire up a minimal console logger so messages are visible
if os.environ.get("SPLURGE_ENABLE_DIAGNOSTICS"):
    logging.basicConfig(level=logging.INFO)
    diag_logger = logging.getLogger("splurge.diagnostics")
    if os.environ.get("SPLURGE_DIAGNOSTICS_VERBOSE"):
        diag_logger.setLevel(logging.DEBUG)

# Associated domains for this module
# Moved to top of module after imports.


def _parse_method_patterns(pattern_args: tuple[str, ...]) -> list[str]:
    """Parse method patterns from CLI arguments.

    Supports both comma-separated values and multiple flags.
    Properly trims whitespace from all values.
    Examples:
        ('setUp,beforeAll', 'teardown') -> ['setUp', 'beforeAll', 'teardown']
        ('  setUp  ,  beforeAll  ',) -> ['setUp', 'beforeAll']
    """
    patterns = []
    for arg in pattern_args:
        # Trim the entire argument first, then split on commas
        trimmed_arg = arg.strip()
        if trimmed_arg:  # Skip empty arguments
            # Split on commas and strip each pattern
            for pattern in trimmed_arg.split(","):
                trimmed_pattern = pattern.strip()
                if trimmed_pattern:  # Skip empty patterns
                    patterns.append(trimmed_pattern)

    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    for pattern in patterns:
        if pattern not in seen:
            seen.add(pattern)
            unique_patterns.append(pattern)

    return unique_patterns


@click.command()
@click.version_option(version=__version__)
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for converted files (default: overwrite in place)",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would be converted without making changes",
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Recursively find unittest files in directories",
)
@click.option(
    "--encoding",
    default="utf-8",
    help="Text encoding for reading/writing files (default: utf-8)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed output",
)
@click.option(
    "--backup",
    "-b",
    type=click.Path(path_type=Path),
    help="Create backup files in specified directory with .bak extension",
)
@click.option(
    "--setup-methods",
    multiple=True,
    help="Setup method patterns (comma-separated or multiple flags). Examples: --setup-methods 'setUp,beforeAll' --setup-methods teardown",
)
@click.option(
    "--teardown-methods",
    multiple=True,
    help="Teardown method patterns (comma-separated or multiple flags)",
)
@click.option(
    "--test-methods",
    multiple=True,
    help="Test method patterns (comma-separated or multiple flags)",
)
# Compatibility mode removed: CLI always emits strict pytest-style output.
@click.option(
    "--autocreate/--no-autocreate",
    default=True,
    help="Enable or disable autocreation of tmp_path-backed file fixtures when a sibling '<prefix>_content' is present (default: --autocreate)",
)
def main(
    paths: tuple[Path, ...],
    output: Path | None,
    dry_run: bool,
    recursive: bool,
    encoding: str,
    verbose: bool,
    backup: Path | None,
    setup_methods: tuple[str, ...],
    teardown_methods: tuple[str, ...],
    test_methods: tuple[str, ...],
    autocreate: bool,
) -> None:
    """Convert unittest-style tests to pytest-style tests.

    PATHS may be individual files or directories. If directories are
    provided, use ``--recursive`` to search them for unittest files.

    Args:
        paths: One or more filesystem paths (files or directories).
        output: Optional output directory; when omitted the converter
            overwrites files in place.
        dry_run: If True, only print potential changes without writing.
        recursive: When True and a directory is supplied, search
            recursively for unittest files.
        encoding: Text encoding used for reading and writing files.
        verbose: When True, print detailed progress messages.
        backup: Optional directory to store backups of files before
            conversion.
        setup_methods: Additional setup method patterns (comma-separated
            or provided across multiple flags).
        teardown_methods: Additional teardown method patterns.
        test_methods: Additional test method patterns.
        autocreate: If True, enable autocreation of tmp_path-backed
            fixtures when a sibling ``<prefix>_content`` file exists.

    The command prints a short summary at completion and exits with status
    code 1 if file-level errors occurred.
    """
    if not paths:
        click.echo("Error: No paths provided", err=True)
        sys.exit(1)

    # Collect all files to process
    files_to_convert: list[Path] = []

    for path in paths:
        if path.is_file():
            files_to_convert.append(path)
        elif path.is_dir():
            if recursive:
                unittest_files = find_unittest_files(path)
                files_to_convert.extend(unittest_files)
                if verbose:
                    click.echo(f"Found {len(unittest_files)} unittest files in {path}")
            else:
                click.echo(
                    f"Warning: {path} is a directory. Use --recursive to search it.",
                    err=True,
                )

    if not files_to_convert:
        click.echo("No unittest files found to convert")
        sys.exit(0)

    # Parse method patterns from CLI arguments
    setup_patterns = parse_method_patterns(setup_methods)
    teardown_patterns = parse_method_patterns(teardown_methods)
    test_patterns = parse_method_patterns(test_methods)

    if verbose and (setup_patterns or teardown_patterns or test_patterns):
        click.echo("Using custom method patterns:")
        if setup_patterns:
            click.echo(f"  Setup: {', '.join(setup_patterns)}")
        if teardown_patterns:
            click.echo(f"  Teardown: {', '.join(teardown_patterns)}")
        if test_patterns:
            click.echo(f"  Test: {', '.join(test_patterns)}")

    # Build an optional PatternConfigurator from parsed CLI patterns so
    # dry-run invocations that call convert_string may consult the
    # configured patterns. For non-dry-run conversions we pass the raw
    # pattern lists into convert_file which will build the configurator.
    pc = None
    if setup_patterns or teardown_patterns or test_patterns:
        pc = PatternConfigurator()
        for p in setup_patterns:
            pc.add_setup_pattern(p)
        for p in teardown_patterns:
            pc.add_teardown_pattern(p)
        for p in test_patterns:
            pc.add_test_pattern(p)

    # Process each file
    converted_count = 0
    error_count = 0

    for file_path in files_to_convert:
        if verbose:
            click.echo(f"Processing: {file_path}")

        try:
            # Create backup if requested
            if backup and not dry_run:
                backup_dir = backup
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_path = backup_dir / f"{file_path.name}.bak"
                try:
                    import shutil

                    shutil.copy2(file_path, backup_path)
                    if verbose:
                        click.echo(f"Backup created: {backup_path}")
                except Exception as e:
                    click.echo(f"Warning: Failed to create backup for {file_path}: {e}", err=True)

            # Determine output path
            if output:
                output_path = output / file_path.name
            else:
                output_path = None  # Will overwrite in place

            # Convert the file
            if dry_run:
                try:
                    from .main import convert_string

                    source_code = file_path.read_text(encoding=encoding)

                    # If the file already imports pytest, treat it as unchanged
                    # for dry-run reporting purposes to avoid noisy diffs.
                    if "import pytest" in source_code or "from pytest" in source_code:
                        result = ConversionResult(
                            original_code=source_code,
                            converted_code=source_code,
                            has_changes=False,
                            errors=[],
                        )
                    else:
                        # Pass the constructed PatternConfigurator so the
                        # dry-run conversion can respect CLI-provided patterns.
                        result = convert_string(source_code, autocreate=autocreate, pattern_config=pc)

                    if result.has_changes:
                        click.echo(f"Would convert: {file_path}")
                        if verbose:
                            click.echo("Changes would be made:")
                            _show_diff_summary(result.original_code, result.converted_code)
                    else:
                        if verbose:
                            click.echo(f"No changes needed: {file_path}")

                    if result.errors:
                        for error in result.errors:
                            click.echo(f"Error in {file_path}: {error}", err=True)
                        error_count += 1
                    elif result.has_changes:
                        converted_count += 1
                except (ParseError, EncodingError) as e:
                    click.echo(f"Error processing {file_path}: {e}", err=True)
                    error_count += 1
                except (SplurgeFileNotFoundError, PermissionDeniedError) as e:
                    click.echo(f"File access error for {file_path}: {e}", err=True)
                    error_count += 1
            else:
                try:
                    # Pass explicit pattern lists into convert_file so it can
                    # construct a PatternConfigurator for the pipeline.
                    result = convert_file(
                        file_path,
                        output_path,
                        encoding=encoding,
                        autocreate=autocreate,
                        setup_patterns=setup_patterns or None,
                        teardown_patterns=teardown_patterns or None,
                        test_patterns=test_patterns or None,
                    )

                    if result.has_changes:
                        click.echo(f"Converted: {file_path}")
                        if verbose and output_path:
                            click.echo(f"  -> {output_path}")
                        converted_count += 1
                    elif verbose:
                        click.echo(f"No changes needed: {file_path}")

                    if result.errors:
                        for error in result.errors:
                            click.echo(f"Error in {file_path}: {error}", err=True)
                        error_count += 1
                except ParseError as e:
                    click.echo(f"Parse error in {file_path}: {e}", err=True)
                    error_count += 1
                except (SplurgeFileNotFoundError, PermissionDeniedError) as e:
                    click.echo(f"File access error for {file_path}: {e}", err=True)
                    error_count += 1
                except EncodingError as e:
                    click.echo(f"Encoding error for {file_path}: {e}", err=True)
                    error_count += 1

        except SplurgeError as e:
            click.echo(f"Error processing {file_path}: {e}", err=True)
            error_count += 1
        except Exception as e:
            click.echo(f"Unexpected error processing {file_path}: {e}", err=True)
            error_count += 1

    # Summary
    total_files = len(files_to_convert)
    click.echo(f"\nProcessed {total_files} files:")

    if dry_run:
        click.echo(f"  {converted_count} files would be converted")
    else:
        click.echo(f"  {converted_count} files converted")

    if error_count > 0:
        click.echo(f"  {error_count} files had errors")

    unchanged_count = total_files - converted_count - error_count
    if unchanged_count > 0:
        click.echo(f"  {unchanged_count} files unchanged")

    if error_count > 0:
        sys.exit(1)


def _show_diff_summary(original: str, converted: str) -> None:
    """Show a brief summary of changes made."""
    original_lines = original.splitlines()
    converted_lines = converted.splitlines()

    # Simple diff summary
    if len(original_lines) != len(converted_lines):
        click.echo(f"    Lines changed: {len(original_lines)} -> {len(converted_lines)}")

    # Count assertion changes (rough heuristic)
    original_asserts = sum(1 for line in original_lines if "self.assert" in line)
    converted_asserts = sum(1 for line in converted_lines if "assert " in line)

    if original_asserts > 0:
        click.echo(f"    Unittest assertions converted: {original_asserts}")
        if converted_asserts > 0:
            click.echo(f"    Pytest assertions created: {converted_asserts}")

    # Check for unittest.TestCase removal
    if any("unittest.TestCase" in line for line in original_lines):
        click.echo("    Removed unittest.TestCase inheritance")

    # Check for pytest import addition
    if any("import pytest" in line or "from pytest" in line for line in converted_lines):
        click.echo("    Added pytest import")


if __name__ == "__main__":
    main()
