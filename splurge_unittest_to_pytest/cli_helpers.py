"""CLI helper functions for the unittest to pytest migration tool.

This module contains utility functions used by the CLI commands,
separated from the main CLI module for better organization.
"""

import logging
import os
from typing import Any

from .context import MigrationConfig
from .events import EventBus


def setup_logging(debug_mode: bool = False) -> None:
    """Set up logging configuration for the application."""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logging_with_level(log_level: str) -> None:
    """Set up logging with a specific level."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def set_quiet_mode(quiet: bool = False) -> None:
    """Set quiet mode by adjusting log levels."""
    if quiet:
        logging.getLogger().setLevel(logging.WARNING)


def create_event_bus() -> EventBus:
    """Create and configure the event bus for the application."""
    return EventBus()


def attach_progress_handlers(event_bus: EventBus, verbose: bool = False) -> None:
    """Attach progress handlers to the event bus."""
    from .events import LoggingSubscriber

    # Create a logging subscriber that handles progress events internally
    LoggingSubscriber(event_bus, verbose=verbose)


def detect_test_prefixes_from_files(source_files: list[str]) -> list[str]:
    """Detect test method prefixes from source files."""
    prefixes = set()

    for file_path in source_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Look for test methods
            import re

            test_methods = re.findall(r"def (test_\w+|spec_\w+|should_\w+|it_\w+)", content)
            for method in test_methods:
                prefixes.add(method.split("_")[0] + "_")

        except (OSError, UnicodeDecodeError):
            # Skip files that can't be read
            continue

    return sorted(prefixes) if prefixes else ["test_"]


def create_config(
    dry_run: bool = False,
    target_root: str | None = None,
    file_patterns: list[str] | None = None,
    recurse: bool = True,
    backup_originals: bool = True,
    backup_root: str | None = None,
    target_suffix: str = "",
    target_extension: str | None = None,
    line_length: int | None = 120,
    assert_almost_equal_places: int = 7,
    log_level: str = "INFO",
    max_file_size_mb: int = 10,
    max_concurrent: int = 4,
    max_depth: int = 10,
    fail_fast: bool = False,
    detect_prefixes: bool = False,
    create_source_map: bool = False,
    test_method_prefixes: list[str] | None = None,
    degradation_tier: str = "essential",
    force: bool = False,
    # Backward compatibility aliases
    suffix: str | None = None,
    ext: str | None = None,
) -> MigrationConfig:
    """Create a basic configuration object from parameters."""
    # Handle backward compatibility aliases
    actual_suffix = suffix if suffix is not None else target_suffix
    actual_extension = ext if ext is not None else target_extension

    # Create base configuration with all parameters
    config_dict = {
        "dry_run": dry_run,
        "target_root": target_root,
        "file_patterns": file_patterns or ["test_*.py"],
        "recurse_directories": recurse,
        "backup_originals": backup_originals,
        "backup_root": backup_root,
        "target_suffix": actual_suffix,
        "target_extension": actual_extension,
        "line_length": line_length,
        "assert_almost_equal_places": assert_almost_equal_places,
        "log_level": log_level,
        "max_file_size_mb": max_file_size_mb,
        "max_concurrent_files": max_concurrent,
        "max_depth": max_depth,
        "fail_fast": fail_fast,
        "create_source_map": create_source_map,
        "test_method_prefixes": test_method_prefixes or ["test"],
        "degradation_tier": degradation_tier,
    }

    # Use from_dict to leverage validation and keep mypy happy about dynamic dicts
    return MigrationConfig.from_dict(config_dict)


def validate_source_files(source_files: list[str]) -> list[str]:
    """Validate and filter source files."""
    valid_files = []

    for file_path in source_files:
        if os.path.isfile(file_path):
            valid_files.append(file_path)
        elif os.path.isdir(file_path):
            # For directories, find all Python files
            for root, _dirs, files in os.walk(file_path):
                for file in files:
                    if file.endswith(".py"):
                        valid_files.append(os.path.join(root, file))
        else:
            # Try to treat as glob pattern
            import glob

            matched_files = glob.glob(file_path)
            valid_files.extend(matched_files)

    return valid_files


def validate_source_files_with_patterns(
    source_files: list[str],
    root_directory: str | None,
    file_patterns: list[str],
    recurse: bool = True,
) -> list[str]:
    """Validate source files with pattern matching."""
    import glob

    valid_files = []

    # Start with any explicitly provided source files
    for file_path in source_files:
        if os.path.isfile(file_path):
            valid_files.append(file_path)

    # If root_directory is provided, find files matching patterns
    if root_directory and os.path.isdir(root_directory):
        for pattern in file_patterns:
            # Create full pattern path
            full_pattern = os.path.join(root_directory, pattern)

            if recurse:
                # Use recursive globbing
                matched_files = glob.glob(full_pattern, recursive=True)
                # Also try with ** prefix for deeper recursion
                if "**" not in full_pattern and ("*" in pattern or "?" in pattern):
                    recursive_pattern = os.path.join(root_directory, "**", pattern)
                    matched_files.extend(glob.glob(recursive_pattern, recursive=True))
            else:
                matched_files = glob.glob(full_pattern)

            # Filter for files only
            for file_path in matched_files:
                if os.path.isfile(file_path) and file_path not in valid_files:
                    valid_files.append(file_path)

    # Remove duplicates
    seen = set()
    unique_valid_files = []
    for file_path in valid_files:
        if file_path not in seen:
            seen.add(file_path)
            unique_valid_files.append(file_path)

    return unique_valid_files


def _handle_enhanced_validation_features(
    base_config: MigrationConfig,
    config_kwargs: dict[str, Any],
) -> MigrationConfig | Any:
    """Handle enhanced validation features in configuration."""
    try:
        # Try to apply enhanced validation
        from .config_validation import (
            ConfigurationAdvisor,
            ConfigurationFieldRegistry,
            ConfigurationTemplateManager,
            ConfigurationUseCaseDetector,
            ValidatedMigrationConfig,
        )

        # Create validated config with enhanced features
        config = ValidatedMigrationConfig(**base_config.__dict__)

        # Apply any additional overrides
        for key, value in config_kwargs.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        # Pydantic model validators run on initialization; avoid calling descriptors directly

        # Handle enhanced CLI features
        if config_kwargs.get("show_suggestions", False):
            advisor = ConfigurationAdvisor()
            # ConfigurationAdvisor provides suggest_improvements
            suggestions = advisor.suggest_improvements(config)
            if suggestions:
                print("\nConfiguration Suggestions:")
                for suggestion in suggestions:
                    # Suggestion dataclass exposes message/action
                    print(f"  • {suggestion.message}")
                    if suggestion.action:
                        print(f"    Action: {suggestion.action}")

        if config_kwargs.get("use_case_analysis", False):
            detector = ConfigurationUseCaseDetector()
            use_case = detector.detect_use_case(config)
            # Detailed analysis API is not available; print detected use case
            print(f"\nDetected Use Case: {use_case}")

        if config_kwargs.get("generate_field_help"):
            registry = ConfigurationFieldRegistry()
            field_name = config_kwargs["generate_field_help"]
            field_info = registry.get_field(field_name)
            if field_info:
                print(f"\nHelp for field '{field_name}':")
                print(f"   Type: {field_info.type}")
                print(f"   Description: {field_info.description}")
                if field_info.examples:
                    print(f"   Examples: {', '.join(field_info.examples)}")
                if field_info.constraints:
                    print(f"   Constraints: {'; '.join(field_info.constraints)}")
                if field_info.common_mistakes:
                    print("   Common Mistakes:")
                    for mistake in field_info.common_mistakes:
                        print(f"     • {mistake}")
            else:
                print(f"\nField '{field_name}' not found.")

        if config_kwargs.get("list_templates", False):
            manager = ConfigurationTemplateManager()
            templates = manager.get_all_templates()
            print("\nAvailable Configuration Templates:")
            for template_name, template in templates.items():
                print(f"  • {template_name}: {template.description}")

        if config_kwargs.get("use_template"):
            manager = ConfigurationTemplateManager()
            template_name = config_kwargs["use_template"]
            template_config = manager.get_template(template_name)
            if template_config:
                print(f"\nApplying template '{template_name}': {template_config.description}")
                # Apply template config to the validated config
                for key, value in template_config.config_dict.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            else:
                print(f"\nTemplate '{template_name}' not found.")

        if config_kwargs.get("generate_docs"):
            from .config_validation import generate_configuration_documentation

            format_type = config_kwargs["generate_docs"]
            docs = generate_configuration_documentation(format_type)
            if format_type == "markdown":
                output_file = "configuration-docs.md"
            elif format_type == "html":
                output_file = "configuration-docs.html"
            else:
                output_file = f"configuration-docs.{format_type}"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(docs)
            print(f"\nConfiguration documentation generated: {output_file}")

        return config

    except Exception as e:
        # If enhanced validation fails, fall back to basic config
        logger = logging.getLogger(__name__)
        logger.warning(f"Enhanced validation failed: {e}. Using basic configuration.")

        # Create basic config without enhanced features
        basic_config = MigrationConfig(**base_config.__dict__)
        for key, value in config_kwargs.items():
            if hasattr(basic_config, key) and value is not None:
                setattr(basic_config, key, value)

        return basic_config


def _apply_defaults_to_config(config: MigrationConfig | None, questions: list) -> MigrationConfig:
    """Apply default values to configuration without prompting."""
    from .context import MigrationConfig

    if config is None:
        config = MigrationConfig()

    # Apply defaults using config.__dict__ for Pydantic compatibility
    config_dict = config.__dict__.copy()

    for question in questions:
        key = question["key"]
        default = question["default"]
        process_func = question.get("process")

        # Only apply if the field exists in the config
        if hasattr(config, key):
            if process_func and isinstance(default, str):
                config_dict[key] = process_func(default)
            else:
                config_dict[key] = default

        # Handle conditional questions
        if question.get("condition") and not question["condition"](config):
            continue

    # Create new config with updated values
    return MigrationConfig(**config_dict)


def _handle_interactive_questions(questions: list) -> MigrationConfig:
    """Handle interactive questions for configuration."""
    from .context import MigrationConfig

    config = MigrationConfig()
    config_dict = config.__dict__.copy()

    for question in questions:
        key = question["key"]
        prompt = question["prompt"]
        question_type = question["type"]
        default = question["default"]
        process_func = question.get("process")
        condition = question.get("condition")

        # Check if question should be asked
        if condition and not condition(config):
            continue

        # Only apply if the field exists in the config
        if hasattr(config, key):
            if question_type == "confirm":
                # Boolean question
                import typer

                value = typer.confirm(prompt, default=default)
                config_dict[key] = value
            elif question_type == "prompt":
                # String question
                import typer

                value = typer.prompt(prompt, default=str(default))
                if process_func:
                    value = process_func(value)
                config_dict[key] = value

    return MigrationConfig(**config_dict)


def prepare_config(
    *,
    base_config: MigrationConfig | None = None,
    interactive: bool = False,
    questions: list | None = None,
    enhanced_kwargs: dict | None = None,
) -> MigrationConfig:
    """Public helper that prepares a MigrationConfig for CLI usage.

    It applies defaults, optionally runs interactive questions, and then
    attempts enhanced validation/features. This wires up the private helpers
    so tests and CLI code can call a single entrypoint.
    """
    from .context import MigrationConfig

    # Start with provided base_config or a default one
    if base_config is None:
        base = MigrationConfig()
    else:
        base = base_config

    # Apply non-interactive defaults if provided
    if questions:
        base = _apply_defaults_to_config(base, questions)

    # If interactive, prompt the user for values and override
    if interactive:
        iq = questions or []
        base = _handle_interactive_questions(iq)

    # Apply enhanced validation/features if available
    if enhanced_kwargs is None:
        enhanced_kwargs = {}

    # Attempt enhanced validation/features, but be resilient to failures
    try:
        final = _handle_enhanced_validation_features(base, enhanced_kwargs)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger = logging.getLogger(__name__)
        logger.warning(f"Enhanced validation/features raised an exception: {exc}; falling back to basic config")
        final = MigrationConfig(**base.__dict__)

    # Normalize returned config to MigrationConfig dataclass for consistent API
    if isinstance(final, MigrationConfig):
        return final

    # If final is a Pydantic model or similar, convert to dict then to MigrationConfig
    try:
        final_dict = getattr(final, "dict", None)
        if callable(final_dict):
            cfg_dict = final.dict()
        else:
            # fallback to __dict__
            cfg_dict = getattr(final, "__dict__", {})
        return MigrationConfig.from_dict(cfg_dict)
    except Exception:
        # As a last resort, return a basic MigrationConfig constructed from base
        return MigrationConfig(**base.__dict__)
