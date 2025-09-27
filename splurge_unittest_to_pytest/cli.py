"""Command-line interface for the unittest-to-pytest migration tool.

This module provides the main CLI entry point and command definitions
using the typer library.
"""

import logging
from pathlib import Path
from typing import cast

import typer

from . import main as main_module
from .context import MigrationConfig
from .events import EventBus, LoggingSubscriber
from .pipeline import PipelineFactory

# Initialize typer app
app = typer.Typer(name="unittest-to-pytest", help="Migrate unittest test suites to pytest format", add_completion=False)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging level.

    Args:
        verbose: Enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger().setLevel(level)

    # Reduce noise from third-party libraries
    logging.getLogger("libcst").setLevel(logging.WARNING)
    logging.getLogger("black").setLevel(logging.WARNING)
    logging.getLogger("isort").setLevel(logging.WARNING)


def create_event_bus() -> EventBus:
    """Create and configure event bus.

    Returns:
        Configured event bus with logging subscriber
    """
    event_bus = EventBus()
    LoggingSubscriber(event_bus)  # Configure logging subscriber
    return event_bus


def create_config(
    target_directory: str | None = None,
    root_directory: str | None = None,
    file_patterns: list[str] | None = None,
    recurse_directories: bool = True,
    preserve_structure: bool = True,
    backup_originals: bool = True,
    convert_classes_to_functions: bool = True,
    merge_setup_teardown: bool = True,
    generate_fixtures: bool = True,
    fixture_scope: str = "function",
    format_code: bool = True,
    optimize_imports: bool = True,
    add_type_hints: bool = False,
    line_length: int | None = 120,
    dry_run: bool = False,
    fail_fast: bool = False,
    parallel_processing: bool = True,
    max_workers: int = 4,
    verbose: bool = False,
    generate_report: bool = True,
    report_format: str = "json",
    test_method_prefixes: list[str] | None = None,
    parametrize: bool = False,
    suffix: str = "",
    ext: str | None = None,
) -> MigrationConfig:
    """Create migration configuration from CLI arguments.

    Args:
        target_directory: Target directory for output files
        preserve_structure: Preserve original directory structure
        backup_originals: Create backup of original files
        convert_classes_to_functions: Convert TestCase classes to functions
        merge_setup_teardown: Merge setUp/tearDown into fixtures
        generate_fixtures: Generate pytest fixtures
        fixture_scope: Scope for generated fixtures
        format_code: Format generated code with black/isort
        optimize_imports: Optimize import statements
        add_type_hints: Add type hints to generated code
        line_length: Maximum line length for formatting
        dry_run: Show what would be done without making changes
        fail_fast: Stop on first error
        parallel_processing: Enable parallel processing
        max_workers: Maximum number of worker processes
        verbose: Enable verbose output
        generate_report: Generate migration report
        report_format: Format for migration report

    Returns:
        Configured MigrationConfig instance
    """
    from .context import FixtureScope
    from .helpers.utility import sanitize_extension, sanitize_suffix

    fixture_scope_enum = FixtureScope(fixture_scope)
    suffix = sanitize_suffix(suffix)
    ext = sanitize_extension(ext)

    return MigrationConfig(
        target_directory=target_directory,
        root_directory=root_directory,
        file_patterns=file_patterns or ["test_*.py"],
        recurse_directories=recurse_directories,
        preserve_structure=preserve_structure,
        backup_originals=backup_originals,
        convert_classes_to_functions=convert_classes_to_functions,
        merge_setup_teardown=merge_setup_teardown,
        generate_fixtures=generate_fixtures,
        fixture_scope=fixture_scope_enum,
        format_code=format_code,
        optimize_imports=optimize_imports,
        add_type_hints=add_type_hints,
        line_length=line_length,
        dry_run=dry_run,
        fail_fast=fail_fast,
        parallel_processing=parallel_processing,
        max_workers=max_workers,
        verbose=verbose,
        generate_report=generate_report,
        report_format=report_format,
        test_method_prefixes=test_method_prefixes or ["test"],
        parametrize=parametrize,
        target_suffix=suffix,
        target_extension=ext,
    )


def validate_source_files(source_files: list[str]) -> list[str]:
    """Validate and expand source file paths.

    Args:
        source_files: List of source file or directory paths

    Returns:
        List of validated source file paths

    Raises:
        typer.Exit: If validation fails
    """
    valid_files = []

    for source in source_files:
        path = Path(source)

        if not path.exists():
            logger.error(f"Source path does not exist: {source}")
            raise typer.Exit(code=1)

        if path.is_file() and path.suffix == ".py":
            valid_files.append(str(path))
        elif path.is_dir():
            # Recursively find all Python files
            for py_file in path.rglob("*.py"):
                valid_files.append(str(py_file))
        else:
            logger.warning(f"Skipping non-Python file: {source}")

    if not valid_files:
        logger.error("No Python files found to process")
        raise typer.Exit(code=1)

    return valid_files


# mypy: ignore-errors


def validate_source_files_with_patterns(
    source_files: list[str], root_directory: str | None, file_patterns: list[str], recurse: bool
) -> list[str]:
    """Validate and expand source files using optional root/patterns.

    - If root_directory is provided, search there using patterns.
    - If no source_files provided, default to root_directory (or ".") and patterns.
    - If source_files include files/dirs, include them in search scope.
    """
    roots: list[Path] = []
    if root_directory:
        roots.append(Path(root_directory))

    if source_files:
        for src in source_files:
            roots.append(Path(src))

    if not roots:
        roots = [Path(".")]

    valid_files: list[str] = []

    def add_if_py(p: Path) -> None:
        if p.is_file() and p.suffix == ".py":
            valid_files.append(str(p))

    for root in roots:
        if not root.exists():
            logger.warning(f"Skipping non-existent path: {root}")
            continue
        if root.is_file():
            add_if_py(root)
            continue
        # Directory: apply patterns
        for pattern in file_patterns:
            if recurse:
                for p in root.rglob(pattern):
                    add_if_py(p)
            else:
                for p in root.glob(pattern):
                    add_if_py(p)

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for f in valid_files:
        if f not in seen:
            seen.add(f)
            deduped.append(f)

    if not deduped:
        logger.error("No Python files found to process")
        raise typer.Exit(code=1) from None

    return deduped


@app.command("migrate")
def migrate(
    source_files: list[str] = typer.Argument(..., help="Source unittest files or directories (use -d/-f to search)"),
    root_directory: str | None = typer.Option(None, "--dir", "-d", help="Root directory for input files"),
    file_patterns: list[str] = typer.Option(
        ["test_*.py"], "--file", "-f", help="Glob patterns for input files (repeatable)"
    ),
    recurse: bool = typer.Option(True, "--recurse", "-r", help="Recurse directories when searching for files"),
    target_directory: str | None = typer.Option(None, "--target-dir", "-t", help="Target directory for output files"),
    preserve_structure: bool = typer.Option(True, "--preserve-structure", help="Preserve original directory structure"),
    backup_originals: bool = typer.Option(True, "--backup", help="Create backup of original files"),
    convert_classes: bool = typer.Option(True, "--convert-classes", help="Convert TestCase classes to functions"),
    merge_setup_teardown: bool = typer.Option(True, "--merge-setup", help="Merge setUp/tearDown into fixtures"),
    generate_fixtures: bool = typer.Option(True, "--fixtures", help="Generate pytest fixtures"),
    fixture_scope: str = typer.Option("function", "--fixture-scope", help="Scope for generated fixtures"),
    format_code: bool = typer.Option(True, "--format", help="Format generated code with black/isort"),
    optimize_imports: bool = typer.Option(True, "--optimize-imports", help="Optimize import statements"),
    add_type_hints: bool = typer.Option(False, "--type-hints", help="Add type hints to generated code"),
    line_length: int | None = typer.Option(120, "--line-length", help="Maximum line length for formatting"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Stop on first error"),
    parallel: bool = typer.Option(True, "--parallel", help="Enable parallel processing"),
    max_workers: int = typer.Option(4, "--workers", help="Maximum number of worker processes"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    generate_report: bool = typer.Option(True, "--report", help="Generate migration report"),
    report_format: str = typer.Option("json", "--report-format", help="Format for migration report"),
    test_method_prefixes: list[str] = typer.Option(
        ["test"], "--prefix", help="Allowed test method prefixes (repeatable)"
    ),
    parametrize: bool = typer.Option(
        False, "--parametrize", help="Attempt conservative subTest -> parametrize conversions"
    ),
    suffix: str = typer.Option("", "--suffix", help="Suffix appended to target filename stem (default: '')"),
    ext: str | None = typer.Option(
        None,
        "--ext",
        help="Override target file extension (e.g. 'py' or '.txt'). Defaults to preserving the original extension.",
    ),
    config_file: str | None = typer.Option(None, "--config", help="Configuration file path"),
) -> None:
    """Migrate unittest files to pytest format.

    This command processes unittest test files and converts them to pytest format,
    preserving test behavior while applying pytest best practices.
    """
    setup_logging(verbose)

    try:
        # Create event bus
        event_bus = create_event_bus()

        # Create configuration
        config = create_config(
            target_directory=target_directory,
            root_directory=root_directory,
            file_patterns=file_patterns,
            recurse_directories=recurse,
            preserve_structure=preserve_structure,
            backup_originals=backup_originals,
            convert_classes_to_functions=convert_classes,
            merge_setup_teardown=merge_setup_teardown,
            generate_fixtures=generate_fixtures,
            fixture_scope=fixture_scope,
            format_code=format_code,
            optimize_imports=optimize_imports,
            add_type_hints=add_type_hints,
            line_length=line_length,
            dry_run=dry_run,
            fail_fast=fail_fast,
            parallel_processing=parallel,
            max_workers=max_workers,
            verbose=verbose,
            generate_report=generate_report,
            report_format=report_format,
            test_method_prefixes=test_method_prefixes,
            parametrize=parametrize,
            suffix=suffix,
            ext=ext,
        )

        # Validate source files
        valid_files = cast(
            list[str], validate_source_files_with_patterns(source_files, root_directory, file_patterns, recurse) or []
        )
        assert isinstance(valid_files, list)
        try:
            num_valid = len(valid_files)  # type: ignore[arg-type]
        except Exception:
            num_valid = 0
        logger.info(f"Found {num_valid} Python files to process")

        # Create pipeline factory
        PipelineFactory(event_bus)  # Initialize factory for future use

        # Delegate heavy lifting to the programmatic API entrypoint so the logic
        # can be exercised from both the CLI and other Python code.
        result = main_module.migrate(valid_files, config=config)

        if result.is_success():
            logger.info("Migration completed!")
            logger.info(f"Migrated: {len(result.data)} files")
        else:
            logger.error(f"Migration failed: {result.error}")
            raise typer.Exit(code=1) from None

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise typer.Exit(code=1) from None


@app.command("version")
def version() -> None:
    """Show the version of unittest-to-pytest."""
    from . import __version__

    typer.echo(f"unittest-to-pytest {__version__}")


@app.command("init-config")
def init_config(output_file: str = typer.Argument("unittest-to-pytest.yaml", help="Output configuration file")) -> None:
    """Initialize a configuration file with default settings.

    This command creates a configuration file with all available options
    set to their default values, which you can then customize.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        logger.error("PyYAML is required for configuration file support. Install with: pip install PyYAML")
        raise typer.Exit(code=1) from None

    # Create default configuration
    default_config = MigrationConfig().to_dict()

    # Add comments to explain options
    config_with_comments = {
        "# unittest-to-pytest Configuration File": None,
        "# This file contains configuration options for the migration tool.": None,
        "# You can override these settings using command-line flags.": None,
        "# Output settings": None,
        "target_directory": default_config["target_directory"],
        "preserve_structure": default_config["preserve_structure"],
        "backup_originals": default_config["backup_originals"],
        "# Transformation settings": None,
        "convert_classes_to_functions": default_config["convert_classes_to_functions"],
        "merge_setup_teardown": default_config["merge_setup_teardown"],
        "generate_fixtures": default_config["generate_fixtures"],
        "fixture_scope": default_config["fixture_scope"],
        "# Code quality settings": None,
        "format_code": default_config["format_code"],
        "optimize_imports": default_config["optimize_imports"],
        "add_type_hints": default_config["add_type_hints"],
        "line_length": default_config["line_length"],
        "# Behavior settings": None,
        "dry_run": default_config["dry_run"],
        "fail_fast": default_config["fail_fast"],
        "parallel_processing": default_config["parallel_processing"],
        "max_workers": default_config["max_workers"],
        "# Reporting settings": None,
        "verbose": default_config["verbose"],
        "generate_report": default_config["generate_report"],
        "report_format": default_config["report_format"],
    }

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(
                {k: v for k, v in config_with_comments.items() if v is not None},
                f,
                default_flow_style=False,
                sort_keys=False,
            )

        logger.info(f"Configuration file created: {output_file}")
        logger.info("Edit this file to customize migration behavior.")

    except Exception as e:
        logger.error(f"Failed to create configuration file: {e}")
        raise typer.Exit(code=1) from None


def main() -> None:
    """Main entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
