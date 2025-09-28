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


def set_quiet_mode(quiet: bool = False) -> None:
    """Lower global logging level to WARNING when quiet mode is requested."""
    if quiet:
        logging.getLogger().setLevel(logging.WARNING)
        # Keep third-party noise down as well
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
    merge_setup_teardown: bool = True,
    format_code: bool = True,
    fixture_scope: str | None = None,
    line_length: int | None = 120,
    dry_run: bool = False,
    fail_fast: bool = False,
    parallel_processing: bool = True,
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
    format_code: Format generated code with black/isort (always applied)
        line_length: Maximum line length for formatting
        dry_run: Show what would be done without making changes
        fail_fast: Stop on first error
    parallel_processing: Enable parallel processing
        verbose: Enable verbose output
        generate_report: Generate migration report
        report_format: Format for migration report
    Returns:
        Configured MigrationConfig instance
    """
    from .context import FixtureScope
    from .helpers.utility import sanitize_extension, sanitize_suffix

    suffix = sanitize_suffix(suffix)
    ext = sanitize_extension(ext)

    base = MigrationConfig()

    # Normalize fixture_scope if provided (accept strings like "function")
    fs = base.fixture_scope
    if fixture_scope is not None:
        try:
            if isinstance(fixture_scope, str):
                fs = FixtureScope(fixture_scope)
            elif isinstance(fixture_scope, FixtureScope):
                fs = fixture_scope
            else:
                fs = FixtureScope(str(fixture_scope))
        except Exception:
            fs = base.fixture_scope

    return MigrationConfig(
        target_directory=target_directory,
        root_directory=root_directory,
        file_patterns=file_patterns or base.file_patterns,
        recurse_directories=recurse_directories,
        preserve_structure=preserve_structure,
        backup_originals=backup_originals,
        convert_classes_to_functions=base.convert_classes_to_functions,
        merge_setup_teardown=merge_setup_teardown,
        generate_fixtures=base.generate_fixtures,
        fixture_scope=fs,
        format_code=True,  # formatting is mandatory
        optimize_imports=base.optimize_imports,
        add_type_hints=base.add_type_hints,
        line_length=line_length,
        dry_run=dry_run,
        fail_fast=fail_fast,
        parallel_processing=parallel_processing,
        verbose=verbose,
        generate_report=generate_report,
        report_format=report_format,
        test_method_prefixes=test_method_prefixes or base.test_method_prefixes,
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
    merge_setup_teardown: bool = typer.Option(True, "--merge-setup", help="Merge setUp/tearDown into fixtures"),
    line_length: int | None = typer.Option(120, "--line-length", help="Maximum line length for formatting"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress informational logging (keeps warnings/errors)"),
    posix: bool = typer.Option(
        False, "--posix", help="Force POSIX-style path separators (use forward slashes) in CLI output"
    ),
    diff: bool = typer.Option(
        False, "--diff", help="When used with --dry-run, show unified diffs instead of the full converted code"
    ),
    list_files: bool = typer.Option(False, "--list", help="When used with --dry-run, list files only (no code shown)"),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Stop on first error"),
    # Note: max_workers/--workers removed from CLI; parallelism is not exposed
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
    set_quiet_mode(quiet)

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
            merge_setup_teardown=merge_setup_teardown,
            format_code=True,
            line_length=line_length,
            dry_run=dry_run,
            fail_fast=fail_fast,
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
        # If dry-run, log what we'd do and then run migrate which will avoid writes
        if config.dry_run:
            logger.info("Dry-run mode enabled. No files will be written.")
            logger.info("Files that would be processed:")
            for f in valid_files:
                logger.info(f"  - {f}")

        result = main_module.migrate(valid_files, config=config)

        if result.is_success():
            logger.info("Migration completed!")
            logger.info(f"Migrated: {len(result.data)} files")

            # If dry-run, the orchestrator may attach the generated/formatted
            # code in the Result.metadata under 'generated_code'. Print it
            # to stdout so users can inspect the conversion without writing.
            if config.dry_run:
                # The main.migrate result.metadata contains a mapping under
                # 'generated_code' of target_file -> generated_code for
                # dry-run. Present it according to dry_run_mode.
                meta = getattr(result, "metadata", None) or {}
                gen_map = {}
                if isinstance(meta, dict):
                    gen = meta.get("generated_code")
                    if isinstance(gen, dict):
                        # Coerce keys to plain strings (Path objects may be present)
                        from pathlib import Path as _P

                        for k, v in gen.items():
                            try:
                                gen_map[str(_P(k))] = v
                            except Exception:
                                gen_map[str(k)] = v
                    elif isinstance(gen, str):
                        # Single-string fallback - map the single target path
                        # reported in result.data to the code
                        path = result.data[0] if isinstance(result.data, list) and result.data else (result.data or "")
                        try:
                            from pathlib import Path as _P

                            gen_map[str(_P(path))] = gen
                        except Exception:
                            gen_map[str(path)] = gen
                # Determine presentation mode from CLI flags (diff/list_files)
                if list_files:
                    for fname in gen_map.keys():
                        # Print filepath using requested format
                        from pathlib import Path as _P

                        p = _P(fname)
                        display = p.as_posix() if posix else str(p)
                        typer.echo(f"== FILES: {display} ==")
                else:
                    import difflib

                    for fname, code in gen_map.items():
                        if diff:
                            # Produce a unified diff between original source and
                            # generated code.
                            try:
                                from pathlib import Path

                                original = Path(fname)
                                # If original path doesn't exist, don't attempt
                                # to guess legacy filenames. We intentionally do
                                # not include fallbacks for old '.pytest.py' names
                                # — the tool now preserves original extensions by
                                # default and users should pass explicit targets
                                # or use the backup/extension flags when needed.

                                orig_text = original.read_text(encoding="utf-8") if original.exists() else ""
                            except Exception:
                                orig_text = ""

                            a = orig_text.splitlines(keepends=True)
                            b = code.splitlines(keepends=True)
                            from pathlib import Path as _P

                            p = _P(fname)
                            display = p.as_posix() if posix else str(p)
                            diff_lines = list(
                                difflib.unified_diff(a, b, fromfile=f"orig:{original}", tofile=f"new:{display}")
                            )
                            typer.echo(f"== DIFF: {display} ==")
                            if diff_lines:
                                typer.echo("".join(diff_lines))
                            else:
                                typer.echo("<no differences detected>")
                        else:
                            # Default printing of the converted pytest code
                            from pathlib import Path as _P

                            p = _P(fname)
                            display = p.as_posix() if posix else str(p)
                            typer.echo(f"== PYTEST: {display} ==")
                            typer.echo(code)
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
        # Note: worker count configuration removed from CLI surface
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
