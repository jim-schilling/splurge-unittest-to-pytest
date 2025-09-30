"""Command-line interface for the unittest-to-pytest migration tool.

This module defines the public CLI commands and utility helpers used by the
`unittest-to-pytest` command-line application. It uses ``typer`` to expose
the program entrypoint while delegating the heavy-lifting to the programmatic
API in :mod:`splurge_unittest_to_pytest.main` so the same logic can be used
from Python code or the CLI.
"""

import logging
from pathlib import Path
from typing import cast

import typer

from . import main as main_module
from .context import MigrationConfig
from .events import (
    EventBus,
    LoggingSubscriber,
    PipelineCompletedEvent,
    PipelineStartedEvent,
    StepCompletedEvent,
    StepStartedEvent,
)
from .pipeline import PipelineFactory

# Initialize typer app
app = typer.Typer(name="unittest-to-pytest", help="Migrate unittest test suites to pytest format", add_completion=False)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


def setup_logging(debug_mode: bool = False) -> None:
    """Configure root logging levels.

    This sets the root logger to ``DEBUG`` when ``debug_mode`` is True and to
    ``INFO`` otherwise. It also reduces verbosity for known noisy third-party
    libraries used by the project.

    Args:
        debug_mode: If True, enable debug-level logging for troubleshooting.
    """
    """
    When debug_mode is False, set the root logger to INFO.

    When debug_mode is True, keep the root logger at INFO but enable
    DEBUG for the package logger only (``splurge_unittest_to_pytest``).
    This prevents noisy third-party libraries from emitting DEBUG logs
    while still providing detailed logs from this project.
    """

    # Keep root at INFO by default to avoid flooding logs with unrelated
    # debug messages from third-party libraries. When verbose is requested
    # enable DEBUG only for this package's logger so callers can inspect
    # internal behavior without external noise.
    root_level = logging.INFO
    logging.getLogger().setLevel(root_level)

    if debug_mode:
        # Enable DEBUG logging for our package namespace only
        logging.getLogger("splurge_unittest_to_pytest").setLevel(logging.DEBUG)

    # Explicitly silence known noisy third-party libraries
    logging.getLogger("libcst").setLevel(logging.WARNING)
    logging.getLogger("black").setLevel(logging.WARNING)
    logging.getLogger("isort").setLevel(logging.WARNING)


def set_quiet_mode(quiet: bool = False) -> None:
    """Reduce logging output for quiet CLI invocations.

    When ``quiet`` is True the root logger is set to ``WARNING`` and known
    third-party libraries are similarly quieted. This is intended for
    scripted or CI usage where informational logging is undesirable.

    Args:
        quiet: If True, set logging to the warning level.
    """
    if quiet:
        logging.getLogger().setLevel(logging.WARNING)
        # Keep third-party noise down as well
        logging.getLogger("libcst").setLevel(logging.WARNING)
        logging.getLogger("black").setLevel(logging.WARNING)
        logging.getLogger("isort").setLevel(logging.WARNING)


def create_event_bus() -> EventBus:
    """Create and configure the application event bus.

    The returned :class:`EventBus` will have a ``LoggingSubscriber`` attached
    so pipeline events are emitted to the configured Python logging
    infrastructure.

    Returns:
        An initialized :class:`EventBus` instance.
    """
    event_bus = EventBus()
    LoggingSubscriber(event_bus)  # Configure logging subscriber
    return event_bus


def attach_progress_handlers(event_bus: EventBus, verbose: bool = False) -> None:
    """Attach simple progress-printing handlers to the event bus.

    Handlers print compact progress updates to stdout using typer.echo.
    They are intentionally lightweight and will be no-ops when ``not verbose`` is
    True so the CLI's verbose mode is respected.
    """
    if not verbose:
        return

    def _on_pipeline_started(event: PipelineStartedEvent) -> None:
        from pathlib import Path

        try:
            src = Path(event.context.source_file)
            tgt = Path(event.context.target_file)
            typer.echo(f"Pipeline started: {src} -> {tgt} (run_id={event.run_id})")
        except Exception:
            typer.echo(f"Pipeline started (run_id={event.run_id})")

    def _on_step_started(event: StepStartedEvent) -> None:
        typer.echo(f"  -> Step: {event.step_name} ({event.step_type})")

    def _on_step_completed(event: StepCompletedEvent) -> None:
        status = event.result.status.name if hasattr(event.result, "status") else "UNKNOWN"
        typer.echo(f"     Completed: {event.step_name} [{status}] in {event.duration_ms:.2f}ms")

    def _on_pipeline_completed(event: PipelineCompletedEvent) -> None:
        status = "SUCCESS" if event.final_result.is_success() else "FAILED"
        typer.echo(f"Pipeline completed: {status} in {event.duration_ms:.2f}ms")

    event_bus.subscribe(PipelineStartedEvent, _on_pipeline_started)
    event_bus.subscribe(StepStartedEvent, _on_step_started)
    event_bus.subscribe(StepCompletedEvent, _on_step_completed)
    event_bus.subscribe(PipelineCompletedEvent, _on_pipeline_completed)


def create_config(
    target_directory: str | None = None,
    root_directory: str | None = None,
    file_patterns: list[str] | None = None,
    recurse_directories: bool = True,
    preserve_structure: bool = True,
    backup_originals: bool = False,
    line_length: int | None = 120,
    dry_run: bool = False,
    fail_fast: bool = False,
    verbose: bool = False,
    generate_report: bool = True,
    report_format: str = "json",
    test_method_prefixes: list[str] | None = None,
    parametrize: bool = False,
    subtest: bool | None = None,
    suffix: str = "",
    ext: str | None = None,
) -> MigrationConfig:
    """Build a :class:`MigrationConfig` from CLI options.

    The CLI intentionally exposes a smaller surface area than the full
    :class:`MigrationConfig` to keep the command simple. This helper maps the
    selected CLI options into a :class:`MigrationConfig` instance used by the
    programmatic API.

    Args:
        target_directory: Target directory for output files. When ``None`` the
            original directory is used (or the configured root).
        root_directory: Optional root directory used when searching by patterns.
        file_patterns: Glob patterns used to locate input files.
        recurse_directories: Whether to recursively search subdirectories.
        preserve_structure: Preserve original directory structure in output.
        backup_originals: Create backup copies of original files before writing.
        line_length: Maximum line length for code formatting (passed to black).
        dry_run: If True do not write files; return generated code in metadata.
        fail_fast: Stop processing on the first encountered error.
        verbose: Enable verbose logging.
        generate_report: Whether to produce a migration report.
        report_format: Format for the migration report (e.g. ``json``).
        test_method_prefixes: Allowed test method name prefixes (repeatable).
        parametrize: Attempt conservative subTest -> parametrize conversions.
        suffix: Suffix appended to the target filename stem.
        ext: Optional override for the target file extension.

    Returns:
        A populated :class:`MigrationConfig` instance ready for use by the
        migration orchestrator.
    """
    from .helpers.utility import sanitize_extension, sanitize_suffix

    suffix = sanitize_suffix(suffix)
    ext = sanitize_extension(ext)

    base = MigrationConfig()

    return MigrationConfig(
        target_directory=target_directory,
        root_directory=root_directory,
        file_patterns=file_patterns or base.file_patterns,
        recurse_directories=recurse_directories,
        preserve_structure=preserve_structure,
        backup_originals=backup_originals,
        # Legacy transformation flags are intentionally not exposed via the CLI.
        # Keep the MigrationConfig minimal here and let defaults apply.
        # Legacy flags are intentionally not exposed in the CLI and default
        # behavior is used. Keep config minimal here.
        line_length=line_length,
        dry_run=dry_run,
        fail_fast=fail_fast,
        verbose=verbose,
        generate_report=generate_report,
        report_format=report_format,
        test_method_prefixes=test_method_prefixes or base.test_method_prefixes,
        parametrize=parametrize,
        subtest=subtest,
        target_suffix=suffix,
        target_extension=ext,
    )


def validate_source_files(source_files: list[str]) -> list[str]:
    """Validate and expand source file and directory inputs.

    This helper accepts a list of paths (files or directories) and returns a
    flattened list of Python source files to process. Non-Python files are
    skipped, and the function will raise a ``typer.Exit`` with a non-zero
    exit code when no valid Python files are found or when an explicitly
    provided path does not exist.

    Args:
        source_files: List of file or directory paths provided on the CLI.

    Returns:
        A list of validated Python file paths as strings.

    Raises:
        typer.Exit: When no Python files are found or a provided path is
            missing.
    """
    valid_files = []

    for source in source_files:
        path = Path(source)

        if not path.exists():
            logger.error(f"Source path does not exist: {source}")
            raise typer.Exit(code=1)

        # When users provide explicit files on the CLI we accept the path as
        # long as it exists. This lets callers pass non-.py test fixtures
        # (for example .txt sample inputs used in examples) or pre-expanded
        # glob results. Directory inputs are still searched recursively but
        # we keep the default patterning behavior in the pattern-based
        # helper.
        if path.is_file():
            valid_files.append(str(path))
        elif path.is_dir():
            # Recursively find all Python files by default
            for py_file in path.rglob("*.py"):
                valid_files.append(str(py_file))
        else:
            logger.warning(f"Skipping unknown path type: {source}")

    if not valid_files:
        logger.error("No Python files found to process")
        raise typer.Exit(code=1)

    return valid_files


# mypy: ignore-errors


def validate_source_files_with_patterns(
    source_files: list[str], root_directory: str | None, file_patterns: list[str], recurse: bool
) -> list[str]:
    """Validate and expand inputs using an optional root directory and
    filename patterns.

    Behavior:
    - When ``root_directory`` is provided, its tree is searched using the
      provided ``file_patterns``.
    - When ``source_files`` are provided they are included in the search
      scope (files are added directly and directories are searched using
      the supplied patterns).
    - When neither ``root_directory`` nor ``source_files`` are provided, the
      current working directory is searched using ``file_patterns``.

    Args:
        source_files: Explicit files or directories provided on the CLI.
        root_directory: Optional base directory to search when patterns are used.
        file_patterns: Glob-style filename patterns to match (e.g. ``test_*.py``).
        recurse: Whether to recurse into subdirectories when searching.

    Returns:
        A deduplicated list of Python file paths matching the search criteria.

    Raises:
        typer.Exit: When no matching Python files are found.
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
        # Respect whatever the glob returned. When users supply explicit
        # filename patterns we should honor them rather than enforcing a
        # .py-only policy. This enables using example fixtures with other
        # extensions (for example '.txt') in dry-run or test scenarios.
        if p.is_file():
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
    preserve_structure: bool = typer.Option(
        True, "--preserve-structure", help="Preserve original directory structure", is_flag=True
    ),
    backup_originals: bool = typer.Option(
        False, "--backup", "-b", help="Create backup of original files", is_flag=True
    ),
    line_length: int | None = typer.Option(120, "--line-length", help="Maximum line length for formatting"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes", is_flag=True
    ),
    posix: bool = typer.Option(
        False, "--posix", help="Force POSIX-style path separators (use forward slashes) in CLI output", is_flag=True
    ),
    diff: bool = typer.Option(
        False,
        "--diff",
        help="When used with --dry-run, show unified diffs instead of the full converted code",
        is_flag=True,
    ),
    list_files: bool = typer.Option(
        False, "--list", help="When used with --dry-run, list files only (no code shown)", is_flag=True
    ),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Stop on first error", is_flag=True),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output", is_flag=True),
    info: bool = typer.Option(False, "--info", help="Enable info logging output", is_flag=True),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging output", is_flag=True),
    generate_report: bool = typer.Option(False, "--report", help="Generate migration report", is_flag=True),
    report_format: str = typer.Option("json", "--report-format", help="Format for migration report"),
    test_method_prefixes: list[str] = typer.Option(
        ["test"], "--prefix", help="Allowed test method prefixes (repeatable)"
    ),
    parametrize: bool = typer.Option(
        False,
        "--parametrize",
        help="(deprecated) Attempt conservative subTest -> parametrize conversions. Use --no-subtest or omit --subtest to parametrize.",
        is_flag=True,
    ),
    subtest: bool = typer.Option(
        False,
        "--subtest",
        help="Preserve unittest.subTest semantics using pytest-subtests when present; default behavior (no flag) is parametrize.",
        is_flag=True,
    ),
    suffix: str = typer.Option("", "--suffix", help="Suffix appended to target filename stem (default: '')"),
    ext: str | None = typer.Option(
        None,
        "--ext",
        help="Override target file extension (e.g. 'py' or '.txt'). Defaults to preserving the original extension.",
    ),
) -> None:
    """Migrate unittest files to pytest format using the orchestrator.

    The CLI command serves as a thin wrapper that prepares the application
    configuration, validates inputs, creates the application event bus, and
    delegates the actual migration work to :func:`splurge_unittest_to_pytest.main.migrate`.

    Args:
        source_files: Source unittest files or directories to process.
        root_directory: Optional root directory to search when using patterns.
        file_patterns: Glob patterns used to discover input files.
        recurse: Recurse directories when searching for files.
        target_directory: Directory where converted files will be written.
        preserve_structure: Preserve the original directory layout when writing output.
        backup_originals: When True create backups of original files prior to overwriting.
        line_length: Maximum line length used by code formatters.
        dry_run: When True, do not write files; return generated code in result metadata.
        debug: Enable debug-level logging output.
        posix: Format displayed file paths using POSIX separators when True.
        diff: When used with --dry-run, show unified diffs rather than full code output.
        list_files: When used with --dry-run, list files only (no code shown).
        fail_fast: Stop processing on the first encountered error.
        verbose: Enable verbose info logging.
        generate_report: Whether to create a migration report.
        report_format: Report output format (e.g. ``json``).
        test_method_prefixes: Allowed test method prefixes.
        parametrize: Attempt conservative subTest -> parametrize conversions.
        suffix: Suffix appended to target filename stem.
        ext: Optional override for output file extension.
    """
    # Validate mutually exclusive flags: verbose and debug cannot be used together
    if info and debug:
        typer.echo("Error: --info and --debug cannot be used together.")
        raise typer.Exit(code=2)

    # Validate mutually exclusive transformation flags
    if parametrize and subtest:
        typer.echo("Error: --parametrize and --subtest are mutually exclusive. Pick one.")
        raise typer.Exit(code=2)

    if debug or info:
        setup_logging(debug)

    set_quiet_mode(debug or info)

    try:
        # Create event bus
        event_bus = create_event_bus()
        # Attach lightweight progress handlers that print to stdout when not quiet
        attach_progress_handlers(event_bus, verbose=verbose)

        # Create configuration
        config = create_config(
            target_directory=target_directory,
            root_directory=root_directory,
            file_patterns=file_patterns,
            recurse_directories=recurse,
            preserve_structure=preserve_structure,
            backup_originals=backup_originals,
            line_length=line_length,
            dry_run=dry_run,
            fail_fast=fail_fast,
            verbose=verbose,
            generate_report=generate_report,
            report_format=report_format,
            test_method_prefixes=test_method_prefixes,
            parametrize=parametrize,
            subtest=subtest,
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
        "target_directory": default_config.get("target_directory"),
        "preserve_structure": default_config.get("preserve_structure"),
        "backup_originals": default_config.get("backup_originals"),
        "# Transformation settings": None,
        # Legacy/removed transformation settings intentionally omitted
        "# Code quality settings": None,
        # Code quality settings: only include supported options
        "line_length": default_config.get("line_length"),
        "# Behavior settings": None,
        "dry_run": default_config.get("dry_run"),
        "fail_fast": default_config.get("fail_fast"),
        # Note: worker count configuration removed from CLI surface
        "# Reporting settings": None,
        "verbose": default_config.get("verbose"),
        "generate_report": default_config.get("generate_report"),
        "report_format": default_config.get("report_format"),
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
