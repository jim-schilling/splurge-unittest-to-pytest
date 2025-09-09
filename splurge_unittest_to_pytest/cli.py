"""Command line interface for splurge-unittest-to-pytest."""

import sys
from pathlib import Path

import click

from . import __version__
from .exceptions import (
    EncodingError,
    FileNotFoundError as SplurgeFileNotFoundError,
    ParseError,
    PermissionDeniedError,
    SplurgeError,
)
from .main import convert_file, find_unittest_files


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
def main(
    paths: tuple[Path, ...],
    output: Path | None,
    dry_run: bool,
    recursive: bool,
    encoding: str,
    verbose: bool,
    backup: Path | None,
) -> None:
    """Convert unittest-style tests to pytest-style tests.
    
    PATHS can be individual files or directories. Files can have any extension.
    If directories are provided, use --recursive to search for unittest files within them.
    
    Examples:
    
        # Convert a single file
        splurge-convert test_example.py
        
        # Convert files with any extension
        splurge-convert test_example.txt test_example.md
        
        # Convert multiple files  
        splurge-convert test_*.py
        
        # Convert all unittest files in a directory
        splurge-convert --recursive tests/
        
        # Dry run to see what would be changed
        splurge-convert --dry-run --recursive tests/
        
        # Convert to a different directory
        splurge-convert --output converted_tests/ test_*.py
        
        # Create backups before conversion
        splurge-convert --backup backups/ test_*.py
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
                    err=True
                )
    
    if not files_to_convert:
        click.echo("No unittest files found to convert")
        sys.exit(0)
    
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
                    result = convert_string(source_code)
                    
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
                    result = convert_file(file_path, output_path, encoding=encoding)
                    
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