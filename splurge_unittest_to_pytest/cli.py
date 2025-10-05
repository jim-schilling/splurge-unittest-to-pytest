"""Command-line interface for the unittest-to-pytest migration tool.

This module defines the public CLI commands and utility helpers used by the
`unittest-to-pytest` command-line application. It uses ``typer`` to expose
the program entrypoint while delegating the heavy-lifting to the programmatic
API in :mod:`splurge_unittest_to_pytest.main` so the same logic can be used
from Python code or the CLI.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import logging
from pathlib import Path
from typing import cast

import typer

from . import main as main_module
from .cli_adapters import build_config_from_cli
from .cli_helpers import (
    _apply_defaults_to_config,
    _handle_enhanced_validation_features,
    _handle_interactive_questions,
    attach_progress_handlers,
    create_config,
    create_event_bus,
    detect_test_prefixes_from_files,
    set_quiet_mode,
    setup_logging,
    setup_logging_with_level,
    validate_source_files,
    validate_source_files_with_patterns,
)

# Enhanced validation imports
# Phase 3: Intelligent Configuration Assistant
from .config_validation import (
    ConfigurationAdvisor,
    ConfigurationUseCaseDetector,
    IntegratedConfigurationManager,
    InteractiveConfigBuilder,
    ProjectAnalyzer,
    generate_configuration_documentation,
    get_field_help,
    get_template,
    list_available_templates,
)
from .context import ContextManager, MigrationConfig

# Error reporting imports
from .error_reporting import (
    ErrorCategory,
    ErrorReporter,
    SmartError,
)
from .pipeline import PipelineFactory

# Initialize typer app
app = typer.Typer(
    name="splurge-unittest-to-pytest", help="Migrate unittest test suites to pytest format", add_completion=False
)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


@app.command("migrate")
def migrate(
    source_files: list[str] = typer.Argument(..., help="Source unittest files or directories (use -d/-f to search)"),
    root_directory: str | None = typer.Option(None, "--dir", "-d", help="Root directory for input files"),
    file_patterns: list[str] = typer.Option(
        ["test_*.py"], "--file", "-f", help="Glob patterns for input files (repeatable)"
    ),
    recurse: bool = typer.Option(True, "--recurse", "-r", help="Recurse directories when searching for files"),
    target_root: str | None = typer.Option(None, "--target-root", "-t", help="Target root directory for output files"),
    skip_backup: bool = typer.Option(False, "--skip-backup", "-sb", help="Skip backup of original files", is_flag=True),
    backup_root: str | None = typer.Option(
        None, "--backup-root", help="Root directory for backup files (preserves folder structure when recursing)"
    ),
    line_length: int | None = typer.Option(120, "--line-length", help="Maximum line length for formatting"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-dry", help="Show what would be done without making changes", is_flag=True
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
        ["test", "spec", "should", "it"], "--prefix", help="Allowed test method prefixes (repeatable)"
    ),
    detect_prefixes: bool = typer.Option(
        False, "--detect-prefixes", help="Auto-detect test method prefixes from source files", is_flag=True
    ),
    assert_places: int = typer.Option(
        7, "--assert-places", help="Default decimal places for assertAlmostEqual transformations (1-15)"
    ),
    log_level: str = typer.Option("INFO", "--log-level", help="Set logging level (DEBUG, INFO, WARNING, ERROR)"),
    max_file_size: int = typer.Option(10, "--max-file-size", help="Maximum file size in MB to process (1-100)"),
    suffix: str = typer.Option("", "--suffix", help="Suffix appended to target filename stem (default: '')"),
    ext: str | None = typer.Option(
        None,
        "--ext",
        help="Override target file extension (e.g. 'py' or '.txt'). Defaults to preserving the original extension.",
    ),
    # Configuration file support
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="YAML configuration file to load settings from (overrides CLI defaults)"
    ),
    # Output formatting control
    format_output: bool = typer.Option(
        True, "--format", help="Format output code with black and isort (recommended for consistency)", is_flag=True
    ),
    no_format_output: bool = typer.Option(
        False,
        "--no-format",
        help="Disable output code formatting (faster but may produce inconsistent style)",
        is_flag=True,
    ),
    # Import handling options
    remove_unused_imports: bool = typer.Option(
        True, "--remove-imports", help="Remove unused unittest imports after transformation (recommended)", is_flag=True
    ),
    no_remove_unused_imports: bool = typer.Option(
        False, "--no-remove-imports", help="Keep unused unittest imports (may leave redundant imports)", is_flag=True
    ),
    preserve_import_comments: bool = typer.Option(
        True, "--preserve-import-comments", help="Preserve comments in import sections", is_flag=True
    ),
    no_preserve_import_comments: bool = typer.Option(
        False, "--no-preserve-import-comments", help="Remove comments in import sections", is_flag=True
    ),
    # Transform selection options
    transform_assertions: bool = typer.Option(
        True,
        "--transform-assertions",
        help="Transform unittest assertions (assertEqual, assertTrue, etc.) to pytest assertions",
        is_flag=True,
    ),
    no_transform_assertions: bool = typer.Option(
        False,
        "--no-transform-assertions",
        help="Keep unittest assertions unchanged (may require manual conversion)",
        is_flag=True,
    ),
    transform_setup_teardown: bool = typer.Option(
        True, "--transform-setup", help="Convert setUp/tearDown methods to pytest fixtures", is_flag=True
    ),
    no_transform_setup_teardown: bool = typer.Option(
        False, "--no-transform-setup", help="Keep setUp/tearDown methods unchanged", is_flag=True
    ),
    transform_subtests: bool = typer.Option(
        True, "--transform-subtests", help="Convert subTest loops to pytest.mark.parametrize", is_flag=True
    ),
    no_transform_subtests: bool = typer.Option(
        False,
        "--no-transform-subtests",
        help="Keep subTest loops unchanged (may require manual conversion)",
        is_flag=True,
    ),
    transform_skip_decorators: bool = typer.Option(
        True, "--transform-skips", help="Convert unittest skip decorators to pytest skip decorators", is_flag=True
    ),
    no_transform_skip_decorators: bool = typer.Option(
        False, "--no-transform-skips", help="Keep unittest skip decorators unchanged", is_flag=True
    ),
    transform_imports: bool = typer.Option(
        True, "--transform-imports", help="Transform unittest imports to pytest imports", is_flag=True
    ),
    no_transform_imports: bool = typer.Option(
        False, "--no-transform-imports", help="Keep unittest imports unchanged", is_flag=True
    ),
    # Processing options
    continue_on_error: bool = typer.Option(
        False,
        "--continue-on-error",
        help="Continue processing when individual files fail (useful for large codebases)",
        is_flag=True,
    ),
    max_concurrent: int = typer.Option(
        1,
        "--max-concurrent",
        help="Maximum files to process concurrently (1-50, use higher values for better performance on multi-core systems)",
    ),
    cache_analysis: bool = typer.Option(
        True, "--cache-analysis", help="Cache analysis results for better performance on repeated runs", is_flag=True
    ),
    no_cache_analysis: bool = typer.Option(
        False, "--no-cache-analysis", help="Disable analysis result caching (slower but uses less memory)", is_flag=True
    ),
    # Advanced options
    preserve_encoding: bool = typer.Option(
        True, "--preserve-encoding", help="Preserve original file encoding when writing output", is_flag=True
    ),
    no_preserve_encoding: bool = typer.Option(
        False, "--no-preserve-encoding", help="Use default encoding for output files", is_flag=True
    ),
    create_source_map: bool = typer.Option(
        False, "--source-map", help="Create source mapping for debugging transformations (advanced users)", is_flag=True
    ),
    max_depth: int = typer.Option(
        7, "--max-depth", help="Maximum depth to traverse nested control flow structures (3-15, default: 7)"
    ),
    # Enhanced validation features
    show_suggestions: bool = typer.Option(
        False, "--suggestions", help="Show intelligent configuration suggestions", is_flag=True
    ),
    use_case_analysis: bool = typer.Option(
        False, "--use-case-analysis", help="Show detected use case analysis", is_flag=True
    ),
    generate_field_help: str | None = typer.Option(
        None, "--field-help", help="Show help for a specific configuration field"
    ),
    list_templates: bool = typer.Option(
        False, "--list-templates", help="List available configuration templates", is_flag=True
    ),
    use_template: str | None = typer.Option(
        None, "--template", help="Use a pre-configured template (e.g., 'basic_migration', 'ci_integration')"
    ),
    generate_docs: str | None = typer.Option(
        None, "--generate-docs", help="Generate configuration documentation (markdown or html)"
    ),
) -> None:
    """Migrate unittest files to pytest format with comprehensive configuration options.

    This command provides extensive control over the migration process including:

    • **File Discovery**: Configurable patterns, directories, and recursion
    • **Transform Selection**: Choose which unittest features to convert
    • **Output Control**: Formatting, encoding, and file handling options
    • **Performance**: Concurrent processing and caching options
    • **Error Handling**: Continue on errors and graceful degradation
    • **YAML Configuration**: Load settings from configuration files

    Examples:
        # Basic usage with custom config file
        splurge-unittest-to-pytest migrate --config my-config.yaml tests/

        # Disable specific transforms
        splurge-unittest-to-pytest migrate --no-transform-assertions tests/

        # Continue processing despite errors
        splurge-unittest-to-pytest migrate --continue-on-error tests/

        # Use multiple prefixes for modern testing
        splurge-unittest-to-pytest migrate --prefix test --prefix spec tests/

    The CLI command serves as a thin wrapper that prepares the application
    configuration, validates inputs, creates the application event bus, and
    delegates the actual migration work to :func:`splurge_unittest_to_pytest.main.migrate`.

    Args:
        source_files: Source unittest files or directories to process.
        root_directory: Optional root directory to search when using patterns.
        file_patterns: Glob patterns used to discover input files.
        recurse: Recurse directories when searching for files.
        target_root: Root directory where converted files will be written.
        backup_originals: When True create backups of original files prior to overwriting.
        backup_root: Root directory for backup files. When specified, backups preserve folder structure.
        line_length: Maximum line length used by code formatters.
        dry_run: When True, do not write files; return generated code in result metadata.
        debug: Enable debug-level logging output.
        posix: Format displayed file paths using POSIX separators when True.
        diff: When used with --dry-run, show unified diffs rather than full code output.
        log_level: Set the logging level for the application.
        max_file_size: Maximum file size in MB to process (larger files may cause memory issues).
        list_files: When used with --dry-run, list files only (no code shown).
        fail_fast: Stop processing on the first encountered error.
        verbose: Enable verbose info logging.
        generate_report: Whether to create a migration report.
        report_format: Report output format (e.g. ``json``).
        test_method_prefixes: Allowed test method prefixes.
        parametrize: Attempt conservative subTest -> parametrize conversions.
        suffix: Suffix appended to target filename stem.
        ext: Optional override for output file extension.
        config_file: YAML configuration file to load settings from.
        format_output: Whether to format output code with black and isort.
        remove_unused_imports: Whether to remove unused unittest imports.
        preserve_import_comments: Whether to preserve comments in import sections.
        transform_assertions: Whether to transform unittest assertions to pytest.
        transform_setup_teardown: Whether to convert setUp/tearDown to pytest fixtures.
        transform_subtests: Whether to convert subTest loops to parametrize.
        transform_skip_decorators: Whether to convert unittest skip decorators.
        transform_imports: Whether to transform unittest imports to pytest.
        continue_on_error: Whether to continue processing when individual files fail.
        max_concurrent: Maximum files to process concurrently.
        cache_analysis: Whether to cache analysis results for performance.
        preserve_encoding: Whether to preserve original file encoding.
        create_source_map: Whether to create source mapping for debugging.
    """
    # Validate mutually exclusive flags: verbose and debug cannot be used together
    if info and debug:
        typer.echo("Error: --info and --debug cannot be used together.")
        raise typer.Exit(code=2)

    # Load configuration from YAML file if provided
    base_config = MigrationConfig()
    if config_file is not None:
        # Convert OptionInfo to string if needed
        config_file_path = str(config_file) if hasattr(config_file, "__str__") else config_file
        try:
            config_result = ContextManager.load_config_from_file(config_file_path)
            if config_result.is_success():
                # config_result.data should be a MigrationConfig; cast for mypy
                base_config = cast(MigrationConfig, config_result.data)
                logger.info(f"Loaded configuration from: {config_file_path}")
            else:
                typer.echo(f"Error loading configuration file: {config_result.error}")
                raise typer.Exit(code=1) from None
        except Exception as e:
            typer.echo(f"Error loading configuration file: {e}")
            raise typer.Exit(code=1) from e

    # Validate source files first to get valid_files for prefix detection
    valid_files = cast(
        list[str], validate_source_files_with_patterns(source_files, root_directory, file_patterns, recurse) or []
    )

    # Auto-detect test prefixes if requested
    effective_prefixes = test_method_prefixes
    if detect_prefixes and valid_files:
        detected_prefixes = detect_test_prefixes_from_files(valid_files)
        if detected_prefixes != test_method_prefixes:
            logger.info(f"Auto-detected test prefixes: {detected_prefixes}")
            effective_prefixes = detected_prefixes

    # Resolve boolean flag conflicts (negative flags override positive ones)
    final_format_output = format_output and not no_format_output
    final_remove_unused_imports = remove_unused_imports and not no_remove_unused_imports
    final_preserve_import_comments = preserve_import_comments and not no_preserve_import_comments
    final_transform_assertions = transform_assertions and not no_transform_assertions
    final_transform_setup_teardown = transform_setup_teardown and not no_transform_setup_teardown
    final_transform_subtests = transform_subtests and not no_transform_subtests
    final_transform_skip_decorators = transform_skip_decorators and not no_transform_skip_decorators
    final_transform_imports = transform_imports and not no_transform_imports
    final_cache_analysis = cache_analysis and not no_cache_analysis
    final_preserve_encoding = preserve_encoding and not no_preserve_encoding

    # Create configuration (decision model always enabled, parametrize always enabled by default)
    # Use base_config as the foundation and override with CLI parameters
    config_kwargs: dict[str, object] = {}

    # Only add CLI parameters that were explicitly provided (not None)
    if target_root is not None:
        config_kwargs["target_root"] = target_root
    if root_directory is not None:
        config_kwargs["root_directory"] = root_directory
    if file_patterns is not None:
        config_kwargs["file_patterns"] = file_patterns
    if recurse is not None:
        config_kwargs["recurse_directories"] = recurse
    config_kwargs["backup_originals"] = not skip_backup
    if backup_root is not None:
        config_kwargs["backup_root"] = backup_root
    if line_length is not None:
        config_kwargs["line_length"] = line_length
    if dry_run is not None:
        config_kwargs["dry_run"] = dry_run
    if fail_fast is not None:
        config_kwargs["fail_fast"] = fail_fast
    if verbose is not None:
        config_kwargs["verbose"] = verbose
    if generate_report is not None:
        config_kwargs["generate_report"] = generate_report
    if report_format is not None:
        config_kwargs["report_format"] = report_format
    if effective_prefixes is not None:
        config_kwargs["test_method_prefixes"] = effective_prefixes
    if assert_places is not None:
        # Extract actual value from OptionInfo if needed
        from typer.models import OptionInfo

        if isinstance(assert_places, OptionInfo):
            config_kwargs["assert_almost_equal_places"] = int(assert_places.default)
        else:
            config_kwargs["assert_almost_equal_places"] = int(assert_places)
    if log_level is not None:
        # Extract actual value from OptionInfo if needed
        from typer.models import OptionInfo

        if isinstance(log_level, OptionInfo):
            config_kwargs["log_level"] = str(log_level.default)
        else:
            config_kwargs["log_level"] = str(log_level)
    if max_file_size is not None:
        # Extract actual value from OptionInfo if needed
        from typer.models import OptionInfo

        if isinstance(max_file_size, OptionInfo):
            config_kwargs["max_file_size_mb"] = int(max_file_size.default)
        else:
            config_kwargs["max_file_size_mb"] = int(max_file_size)
    if suffix is not None:
        config_kwargs["target_suffix"] = str(suffix)
    if ext is not None:
        config_kwargs["target_extension"] = str(ext)

    # Add new configuration options
    config_kwargs["format_output"] = final_format_output
    config_kwargs["remove_unused_imports"] = final_remove_unused_imports
    config_kwargs["preserve_import_comments"] = final_preserve_import_comments
    config_kwargs["transform_assertions"] = final_transform_assertions
    config_kwargs["transform_setup_teardown"] = final_transform_setup_teardown
    config_kwargs["transform_subtests"] = final_transform_subtests
    config_kwargs["transform_skip_decorators"] = final_transform_skip_decorators
    config_kwargs["transform_imports"] = final_transform_imports
    config_kwargs["continue_on_error"] = continue_on_error
    # Extract actual value from OptionInfo if needed
    from typer.models import OptionInfo

    if isinstance(max_concurrent, OptionInfo):
        config_kwargs["max_concurrent_files"] = int(max_concurrent.default)
    else:
        config_kwargs["max_concurrent_files"] = int(max_concurrent)
    config_kwargs["cache_analysis_results"] = final_cache_analysis
    config_kwargs["preserve_file_encoding"] = final_preserve_encoding
    config_kwargs["create_source_map"] = create_source_map
    # Extract actual value from OptionInfo if needed
    if isinstance(max_depth, OptionInfo):
        config_kwargs["max_depth"] = int(max_depth.default)
    else:
        config_kwargs["max_depth"] = int(max_depth)

    # Create configuration with enhanced validation, but handle gracefully
    try:
        # Use adapters at the CLI boundary to coerce OptionInfo/runtime values
        config = build_config_from_cli(base_config, config_kwargs)
    except ValueError as e:
        # If enhanced validation fails, try to create config without enhanced features
        # This allows CLI to work even with configurations that would normally fail validation
        if "Configuration conflicts detected" in str(e):
            # Remove enhanced validation features and try again
            logger.warning(f"Configuration validation failed: {e}")
            logger.info("Attempting to create configuration without enhanced validation...")

            # Create a copy of config_kwargs without enhanced validation features
            basic_config_kwargs = config_kwargs.copy()
            # Don't add enhanced validation features for now
            # basic_config_kwargs.pop("show_suggestions", None)
            # basic_config_kwargs.pop("use_case_analysis", None)

            try:
                config = build_config_from_cli(base_config, basic_config_kwargs)
                logger.info("Successfully created configuration without enhanced validation features.")
            except Exception as fallback_error:
                logger.error(f"Failed to create even basic configuration: {fallback_error}")
                raise typer.Exit(code=1) from e
        else:
            # Re-raise other validation errors
            raise

    # Set up logging based on configuration
    if debug or info:
        setup_logging(debug)
    elif hasattr(config, "log_level"):
        # Set logging level based on configuration
        config_log_level = getattr(config, "log_level", "INFO")
        # Ensure log_level is a string, not an OptionInfo object
        if hasattr(config_log_level, "upper"):
            setup_logging_with_level(str(config_log_level))
        else:
            setup_logging_with_level("INFO")

    # Default behavior: quiet when neither debug nor info are set
    set_quiet_mode(not (debug or info))

    try:
        # Create event bus
        event_bus = create_event_bus()
        # Attach lightweight progress handlers that print to stdout when not quiet
        attach_progress_handlers(event_bus, verbose=verbose)
        assert isinstance(valid_files, list)
        num_valid = len(valid_files)
        logger.info(f"Found {num_valid} Python files to process")

        # Handle enhanced validation features as part of migration workflow
        if (
            show_suggestions
            or use_case_analysis
            or generate_field_help
            or list_templates
            or use_template
            or generate_docs
        ):
            config_kwargs = {}
            if show_suggestions is not False:
                config_kwargs["show_suggestions"] = show_suggestions
            if use_case_analysis is not False:
                config_kwargs["use_case_analysis"] = use_case_analysis
            if generate_field_help is not None:
                config_kwargs["generate_field_help"] = generate_field_help
            if list_templates is not False:
                config_kwargs["list_templates"] = list_templates
            if use_template is not None:
                config_kwargs["use_template"] = use_template
            if generate_docs is not None:
                config_kwargs["generate_docs"] = generate_docs

            config = _handle_enhanced_validation_features(config, config_kwargs)

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

        result = main_module.migrate(valid_files, config=config, event_bus=event_bus)

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
                            except (TypeError, ValueError, OSError):
                                gen_map[str(k)] = v
                    elif isinstance(gen, str):
                        # Single-string fallback - map the single target path
                        # reported in result.data to the code
                        path = result.data[0] if isinstance(result.data, list) and result.data else (result.data or "")
                        try:
                            from pathlib import Path as _P

                            gen_map[str(_P(path))] = gen
                        except (TypeError, ValueError, OSError):
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
                            except (FileNotFoundError, PermissionError, UnicodeDecodeError, OSError):
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
    """Show the version of splurge-unittest-to-pytest."""
    from . import __version__

    typer.echo(f"splurge-unittest-to-pytest {__version__}")


@app.command("templates")
def list_templates_cmd() -> None:
    """List available configuration templates."""
    templates = list_available_templates()
    typer.echo("Available configuration templates:")
    for template in templates:
        template_obj = get_template(template)
        if template_obj:
            typer.echo(f"  - {template}: {template_obj.description}")
    typer.echo(f"\nTotal: {len(templates)} templates available")


@app.command("template-info")
def template_info(template_name: str = typer.Argument(..., help="Name of the template to show info for")) -> None:
    """Show detailed information about a specific template."""
    template = get_template(template_name)
    if template:
        typer.echo(f"Template: {template.name}")
        typer.echo(f"Description: {template.description}")
        typer.echo(f"Use case: {template.use_case}")
        typer.echo("\nYAML Configuration:")
        typer.echo(template.to_yaml())
        typer.echo("\nCLI Arguments:")
        typer.echo(f"splurge-unittest-to-pytest migrate {template.to_cli_args()}")
    else:
        typer.echo(f"Error: Template '{template_name}' not found.")
        available = list_available_templates()
        typer.echo(f"Available templates: {', '.join(available)}")


@app.command("field-help")
def field_help_cmd(
    field_name: str = typer.Argument(..., help="Name of the configuration field to get help for"),
) -> None:
    """Show help for a specific configuration field."""
    help_text = get_field_help(field_name)
    typer.echo(help_text)


@app.command("generate-docs")
def generate_docs_cmd(
    output_file: str | None = typer.Option(None, help="Output file (default: stdout)"),
    format: str = typer.Option("markdown", help="Output format (markdown or html)"),
) -> None:
    """Generate configuration documentation."""
    if format not in ["markdown", "html"]:
        typer.echo(f"Error: Format must be 'markdown' or 'html', got '{format}'")
        raise typer.Exit(code=1)

    typer.echo(f"Generating {format} documentation...")
    docs = generate_configuration_documentation(format)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(docs)
        typer.echo(f"Documentation saved to: {output_file}")
    else:
        typer.echo(docs)

    typer.echo(f"Generated {len(docs)} characters of documentation.")


@app.command("generate-templates")
def generate_templates_cmd(
    output_dir: str = typer.Option("./templates", help="Directory to save template files"),
    format: str = typer.Option("yaml", help="Template format (yaml or json)"),
) -> None:
    """Generate configuration template files for all use cases.

    This command creates individual configuration files for each available template,
    making it easy to use pre-configured settings for common scenarios.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Import template manager
    from .config_validation import get_configuration_template_manager

    template_manager = get_configuration_template_manager()
    templates = template_manager.get_all_templates()

    generated_files = []

    for template_name, template in templates.items():
        filename = f"{template_name}.{format}"
        filepath = output_path / filename

        if format == "yaml":
            content = template.to_yaml()
        elif format == "json":
            import json

            content = json.dumps(template.config_dict, indent=2)
        else:
            typer.echo(f"Error: Unsupported format '{format}'. Use 'yaml' or 'json'.")
            raise typer.Exit(code=1) from None

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            generated_files.append(str(filepath))
        except Exception as e:
            typer.echo(f"Error writing template file {filepath}: {e}")
            continue

    typer.echo(f"Generated {len(generated_files)} template files in {output_dir}:")
    for file in generated_files:
        typer.echo(f"  - {file}")

    typer.echo("\nTo use a template, run:")
    typer.echo(f"  splurge-unittest-to-pytest migrate --config {output_dir}/basic_migration.yaml tests/")


@app.command("init-config")
def init_config(
    output_file: str = typer.Argument("splurge-unittest-to-pytest.yaml", help="Output configuration file"),
) -> None:
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
        "# splurge-unittest-to-pytest Configuration File": None,
        "# This file contains configuration options for the migration tool.": None,
        "# You can override these settings using command-line flags.": None,
        "# Output settings": None,
        "target_root": default_config.get("target_root"),
        "backup_originals": default_config.get("backup_originals"),
        "backup_root": default_config.get("backup_root"),
        "target_suffix": default_config.get("target_suffix"),
        "target_extension": default_config.get("target_extension"),
        "# Transformation settings": None,
        "line_length": default_config.get("line_length"),
        "assert_almost_equal_places": default_config.get("assert_almost_equal_places"),
        "log_level": default_config.get("log_level"),
        "max_file_size_mb": default_config.get("max_file_size_mb"),
        "# Behavior settings": None,
        "dry_run": default_config.get("dry_run"),
        "fail_fast": default_config.get("fail_fast"),
        "continue_on_error": default_config.get("continue_on_error"),
        "max_concurrent_files": default_config.get("max_concurrent_files"),
        "# Reporting settings": None,
        "verbose": default_config.get("verbose"),
        "generate_report": default_config.get("generate_report"),
        "report_format": default_config.get("report_format"),
        "# Test discovery settings": None,
        "file_patterns": default_config.get("file_patterns"),
        "recurse_directories": default_config.get("recurse_directories"),
        "test_method_prefixes": default_config.get("test_method_prefixes"),
        "# Output formatting control": None,
        "format_output": default_config.get("format_output"),
        "# Import handling options": None,
        "remove_unused_imports": default_config.get("remove_unused_imports"),
        "preserve_import_comments": default_config.get("preserve_import_comments"),
        "# Transform selection options": None,
        "transform_assertions": default_config.get("transform_assertions"),
        "transform_setup_teardown": default_config.get("transform_setup_teardown"),
        "transform_subtests": default_config.get("transform_subtests"),
        "transform_skip_decorators": default_config.get("transform_skip_decorators"),
        "transform_imports": default_config.get("transform_imports"),
        "# Processing options": None,
        "cache_analysis_results": default_config.get("cache_analysis_results"),
        "# Advanced options": None,
        "preserve_file_encoding": default_config.get("preserve_file_encoding"),
        "create_source_map": default_config.get("create_source_map"),
        "max_depth": default_config.get("max_depth"),
        "# Enhanced validation features": None,
        "show_suggestions": False,
        "use_case_analysis": False,
        "generate_field_help": None,
        "list_templates": False,
        "use_template": None,
        "generate_docs": None,
        "# Degradation settings": None,
        "degradation_enabled": default_config.get("degradation_enabled"),
        "degradation_tier": default_config.get("degradation_tier"),
    }

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        logger.error("PyYAML is required for template generation. Install with: pip install PyYAML")
        raise typer.Exit(code=1) from None

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


@app.command("error-recovery")
def error_recovery_cmd(
    error_message: str = typer.Option(..., "--error", "-e", help="Error message to analyze"),
    category: str = typer.Option(
        "auto",
        help="Error category (auto, configuration, filesystem, parsing, transformation, validation, permission, dependency)",
    ),
    context: str | None = typer.Option(None, help="Additional context as JSON string"),
    interactive: bool = typer.Option(True, help="Run in interactive mode"),
    workflow_only: bool = typer.Option(False, help="Show only recovery workflow, not suggestions"),
) -> None:
    """Interactive error recovery assistant.

    This command provides intelligent suggestions and recovery workflows for common errors
    encountered during unittest to pytest migration.
    """
    import json

    # Initialize error reporter
    reporter = ErrorReporter()

    # Parse category
    if category == "auto":
        # Auto-detect category from error message
        if any(term in error_message.lower() for term in ["config", "parameter", "option"]):
            error_category = ErrorCategory.CONFIGURATION
        elif any(term in error_message.lower() for term in ["file", "directory", "path"]):
            error_category = ErrorCategory.FILESYSTEM
        elif any(term in error_message.lower() for term in ["parse", "syntax", "invalid"]):
            error_category = ErrorCategory.PARSING
        elif any(term in error_message.lower() for term in ["transform", "convert"]):
            error_category = ErrorCategory.TRANSFORMATION
        elif any(term in error_message.lower() for term in ["permission", "access", "forbidden"]):
            error_category = ErrorCategory.PERMISSION
        elif any(term in error_message.lower() for term in ["import", "module", "package"]):
            error_category = ErrorCategory.DEPENDENCY
        else:
            error_category = ErrorCategory.UNKNOWN
    else:
        try:
            error_category = ErrorCategory(category.lower())
        except ValueError:
            typer.echo(
                f"Error: Invalid category '{category}'. Valid options: auto, configuration, filesystem, parsing, transformation, validation, permission, dependency"
            )
            raise typer.Exit(code=1) from None

    # Parse context if provided
    context_dict = {}
    if context:
        try:
            context_dict = json.loads(context)
        except json.JSONDecodeError as e:
            typer.echo(f"Warning: Invalid JSON context: {e}. Using empty context.")

    # Create SmartError for analysis
    smart_error = SmartError(message=error_message, category=error_category, context=context_dict)

    # Generate suggestions
    suggestions = reporter.suggestion_engine.generate_suggestions(smart_error)

    if not workflow_only:
        typer.echo(f"\nError Analysis: {error_category.value.upper()}")
        typer.echo(f"Severity: {reporter.severity_assessor.assess_severity(smart_error).value.upper()}")
        typer.echo(f"Recoverable: {'Yes' if smart_error.is_recoverable() else 'No'}")

        if suggestions:
            typer.echo(f"\nSuggestions ({len(suggestions)} found):")
            for i, suggestion in enumerate(smart_error.get_prioritized_suggestions()[:5], 1):
                typer.echo(f"\n  {i}. [{suggestion.category or 'GENERAL'}] {suggestion.message}")
                typer.echo(f"     Action: {suggestion.action}")
                if suggestion.examples:
                    typer.echo(f"     Examples: {', '.join(suggestion.examples)}")
        else:
            typer.echo("\nNo specific suggestions available for this error.")

    # Get recovery workflow
    workflow = reporter.get_recovery_workflow(smart_error)

    if workflow:
        typer.echo(f"\nRecovery Workflow: {workflow.title}")
        if workflow.description:
            typer.echo(f"   {workflow.description}")

        typer.echo(f"\nEstimated time: {workflow.estimated_time or 'Unknown'}")
        typer.echo(
            f"Success rate: {workflow.success_rate * 100:.0f}%" if workflow.success_rate else "Success rate: Unknown"
        )

        typer.echo("\nRecovery Steps:")
        for i, step in enumerate(workflow.steps or [], 1):
            typer.echo(f"\n  {i}. {step.description}")
            typer.echo(f"     Action: {step.action}")
            if step.examples:
                typer.echo(f"     Examples: {', '.join(step.examples)}")
            if step.validation:
                typer.echo(f"     Validation: {step.validation}")

        # Interactive mode
        if interactive:
            typer.echo("\nInteractive Recovery Mode")
            typer.echo("Would you like to proceed with the first recovery step? (y/n)")

            response = input().strip().lower()
            if response in ["y", "yes"]:
                typer.echo(f"\nExecuting step 1: {workflow.steps[0].description}")
                typer.echo(f"Action: {workflow.steps[0].action}")
                if workflow.steps[0].examples:
                    typer.echo(f"Example: {workflow.steps[0].examples[0]}")

                typer.echo("\nApply this fix and then re-run your migration command.")
            else:
                typer.echo("\nRecovery workflow saved for reference.")
    else:
        typer.echo("\nNo recovery workflow available for this error type.")
        typer.echo("Consider reviewing the suggestions above and checking the documentation.")


@app.command("configure")
def configure_cmd(
    project_root: str = typer.Option(".", help="Root directory of the project to analyze"),
    output_file: str | None = typer.Option(None, help="Save configuration to file (YAML format)"),
    analyze_only: bool = typer.Option(False, help="Only analyze project, don't create configuration"),
    silent: bool = typer.Option(False, help="Run without interactive prompts, use defaults only"),
) -> None:
    """Interactive configuration builder with intelligent project analysis.

    This command analyzes your project structure and guides you through creating
    an optimal configuration for unittest to pytest migration.
    """

    typer.echo("Interactive Configuration Builder")
    typer.echo("This wizard will analyze your project and help create an optimal configuration.")

    # Initialize components
    analyzer = ProjectAnalyzer()
    builder = InteractiveConfigBuilder()

    # Initialize manager with required components
    manager = IntegratedConfigurationManager()

    manager.analyzer = ConfigurationUseCaseDetector()
    manager.advisor = ConfigurationAdvisor()

    # Analyze project
    typer.echo(f"\nAnalyzing project in: {project_root}")
    try:
        analysis = analyzer.analyze_project(project_root)
        typer.echo("Project analysis complete!")

        # Show analysis results
        typer.echo("\nProject Analysis Results:")
        typer.echo(f"   Found {len(analysis['test_files'])} test files")
        typer.echo(f"   Detected test prefixes: {', '.join(sorted(analysis['test_prefixes']))}")
        typer.echo(f"   Project type: {analysis['project_type'].value}")
        typer.echo(f"   Complexity score: {analysis['complexity_score']}")

        if analyze_only:
            typer.echo("\nAnalysis complete. Use --output-file to save configuration.")
            return

        # Build configuration interactively
        config, interaction_data = builder.build_configuration_interactive()

        # Handle questions
        if silent:
            typer.echo("Running in silent mode, using defaults...")
            # Use defaults without prompting
            config = _apply_defaults_to_config(config, interaction_data["questions"])
        else:
            typer.echo("Interactive Configuration Builder")
            typer.echo("This wizard will help you configure unittest to pytest migration.")

            # Show project type detection
            project_type = interaction_data["project_type"]
            typer.echo(f"\nDetected project type: {project_type.value.replace('_', ' ').title()}")

            # Handle questions
            config = _handle_interactive_questions(interaction_data["questions"])

        # Validate and enhance
        typer.echo("\nValidating and enhancing configuration...")
        result = manager.validate_and_enhance_config(config.__dict__)

        if result.success and result.config:
            typer.echo("\nConfiguration complete and validated!")
            # Save to file if requested
            if output_file:
                import yaml

                config_dict = {k: v for k, v in result.config.__dict__.items() if v is not None and v != []}

                with open(output_file, "w", encoding="utf-8") as f:
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)

                typer.echo(f"Configuration saved to: {output_file}")

                # Show usage example
                typer.echo("\nUsage:")
                typer.echo(f"   splurge-unittest-to-pytest migrate --config {output_file} [files...]")
            else:
                typer.echo("\nConfiguration ready! Use with:")
                typer.echo("   splurge-unittest-to-pytest migrate [options] [files...]")
        else:
            typer.echo("\nConfiguration validation failed:")
            for error in result.errors or []:
                typer.echo(f"   - {error['message']}")

            if result.warnings:
                typer.echo("\nWarnings:")
                for warning in result.warnings:
                    typer.echo(f"   - {warning}")

    except Exception as e:
        typer.echo(f"Project analysis failed: {e}")
        typer.echo("Please check the project directory and try again.")
        raise typer.Exit(code=1) from e


__all__ = [
    "create_config",
    "create_event_bus",
    "attach_progress_handlers",
    "validate_source_files",
    "validate_source_files_with_patterns",
]


def main() -> None:
    """Main entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
