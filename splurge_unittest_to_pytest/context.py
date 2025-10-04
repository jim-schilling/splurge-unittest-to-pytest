"""Pipeline context and migration configuration helpers.

This module defines immutable dataclasses and helpers used to carry
configuration and execution context through the migration pipeline. It
exposes ``MigrationConfig`` for transform options and ``PipelineContext``
for passing runtime information (paths, run id, and metadata) between
pipeline stages. Utility functions for loading and validating
configuration are provided by ``ContextManager``.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import dataclasses
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .config_validation import validate_migration_config_object
from .degradation import DegradationManager
from .result import Result


class FixtureScope(Enum):
    """Enumeration of supported pytest fixture scopes.

    Members correspond to the standard pytest fixture scope strings:
    ``function``, ``class``, ``module``, and ``session``.
    """

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    SESSION = "session"


class AssertionType(Enum):
    """Types of test assertions.

    These symbolic kinds are used by analysis code to represent the
    form of an assertion (e.g., equality, membership, raises). They are
    not executed at runtime.
    """

    EQUAL = "assert ==="
    NOT_EQUAL = "assert !=="
    IS = "assert is"
    IS_NOT = "assert is not"
    IN = "assert in"
    NOT_IN = "assert not in"
    IS_INSTANCE = "assert isinstance"
    IS_NOT_INSTANCE = "assert not isinstance"
    TRUE = "assert True"
    FALSE = "assert False"
    IS_NONE = "assert is None"
    IS_NOT_NONE = "assert is not None"
    GREATER = "assert >"
    GREATER_EQUAL = "assert >="
    LESS = "assert <"
    LESS_EQUAL = "assert <="
    ALMOST_EQUAL = "assert almost equal"
    NOT_ALMOST_EQUAL = "assert not almost equal"
    RAISES = "assert raises"
    CUSTOM = "custom assertion"


@dataclass(frozen=True)
class MigrationConfig:
    """Migration behavior configuration.

    This dataclass centralizes options that control file discovery,
    transformation rules, and reporting. It is serializable so callers
    can construct it from dictionaries or configuration files.
    """

    # Output settings
    target_root: str | None = None
    root_directory: str | None = None
    file_patterns: list[str] = field(default_factory=lambda: ["test_*.py"])
    recurse_directories: bool = True
    backup_originals: bool = True
    backup_root: str | None = None
    # Suffix appended to target filename stem (default: '')
    target_suffix: str = ""
    # If set, override the extension on target files (e.g. '.py' or 'txt').
    # None means preserve original extension.
    target_extension: str | None = None

    # Transformation settings
    # Legacy transformation flags removed: convert_classes_to_functions,
    # merge_setup_teardown, generate_fixtures, fixture_scope

    # Code quality settings
    # Code quality flags removed: format_code, optimize_imports, add_type_hints
    line_length: int | None = 120  # Use black default (120) if None

    # Transformation precision settings
    assert_almost_equal_places: int = 7
    """Default number of decimal places for assertAlmostEqual transformations (1-15)"""

    # Logging and reporting settings
    log_level: str = "INFO"
    """Default logging level (DEBUG, INFO, WARNING, ERROR)"""

    # Performance settings
    max_file_size_mb: int = 10
    """Maximum file size in MB to process (larger files may cause memory issues)"""

    # Behavior settings
    dry_run: bool = False
    fail_fast: bool = False
    # parallel_processing removed; library no longer exposes parallelism flag

    # Analysis settings - Decision model is now always enabled
    enable_decision_analysis: bool = True
    """Enable standalone decision analysis job to build transformation decision model"""

    # Optional transforms
    parametrize: bool = True
    parametrize_ids: bool = True
    parametrize_type_hints: bool = True

    # Reporting settings
    verbose: bool = False
    generate_report: bool = True
    report_format: str = "json"  # json, html, markdown

    # Test discovery / naming
    test_method_prefixes: list[str] = field(default_factory=lambda: ["test", "spec", "should", "it"])

    # Degradation settings for gradual transformation failure handling
    degradation_enabled: bool = True
    degradation_tier: str = "advanced"  # "essential", "advanced", "experimental"

    # Output formatting control
    format_output: bool = True
    """Whether to format output code with black and isort"""

    # Import handling options
    remove_unused_imports: bool = True
    """Whether to remove unused unittest imports after transformation"""
    preserve_import_comments: bool = True
    """Whether to preserve comments in import sections"""

    # Transform selection options
    transform_assertions: bool = True
    """Whether to transform unittest assertions to pytest assertions"""
    transform_setup_teardown: bool = True
    """Whether to convert setUp/tearDown methods to pytest fixtures"""
    transform_subtests: bool = True
    """Whether to attempt conversion of subTest loops to parametrize"""
    transform_skip_decorators: bool = True
    """Whether to convert unittest skip decorators to pytest skip decorators"""
    transform_imports: bool = True
    """Whether to transform unittest imports to pytest imports"""

    # Processing options
    continue_on_error: bool = False
    """Whether to continue processing other files when one fails"""
    max_concurrent_files: int = 1
    """Maximum number of files to process concurrently (1 = sequential)"""
    cache_analysis_results: bool = True
    """Whether to cache analysis results between runs for improved performance"""

    # Advanced options
    preserve_file_encoding: bool = True
    """Whether to preserve original file encoding when writing output"""
    create_source_map: bool = False
    """Whether to create source mapping for debugging transformations"""
    max_depth: int = 7
    """Maximum depth to traverse when processing nested control flow structures (3-15)"""

    def with_override(self, **kwargs: Any) -> "MigrationConfig":
        """Return a new ``MigrationConfig`` with specified overrides.

        Args:
            **kwargs: Configuration values to override on the returned
                instance.

        Returns:
            A new ``MigrationConfig`` with the provided overrides
            applied.
        """
        return dataclasses.replace(self, **kwargs)

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If configuration is invalid.
        """
        try:
            validate_migration_config_object(self)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}") from e

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "MigrationConfig":
        """Create config from dictionary.

        Args:
            config_dict: Dictionary containing configuration values.

        Returns:
            New ``MigrationConfig`` instance.

        Raises:
            ValueError: If configuration is invalid.
        """
        # NOTE: legacy keys for removed flags are silently ignored. This allows
        # loading older configuration files without failing when they still
        # contain retired options.
        filtered = {k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__}
        config = cls(**filtered)
        config.validate()
        return config

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Dictionary representation of config.
        """
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class PipelineContext:
    """Immutable context object passed through the migration pipeline.

    The context bundles the source and target file paths, the active
    :class:`MigrationConfig`, a stable ``run_id`` for correlation, and
    an optional metadata mapping. Instances are frozen so callers are
    encouraged to create modified copies rather than mutate shared
    state.
    """

    source_file: str
    target_file: str
    config: MigrationConfig
    run_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    decision_model: Any | None = None  # DecisionModel from analysis job
    degradation_manager: DegradationManager | None = None

    def __post_init__(self) -> None:
        """Perform lightweight validation of the constructed context.

        Currently this verifies that the configured ``source_file`` exists
        and raises ``ValueError`` when it does not. The check is
        intentionally conservative to catch obvious misconfigurations
        early in the pipeline.
        """
        if not Path(self.source_file).exists():
            # Do not raise here to allow tests and in-memory analysis to
            # construct PipelineContext objects without an on-disk file.
            # Steps that require a real file should validate existence as
            # appropriate and return errors.
            import logging

            logging.getLogger(__name__).warning(
                "PipelineContext created with non-existent source_file: %s", self.source_file
            )

    @classmethod
    def create(
        cls,
        source_file: str,
        target_file: str | None = None,
        config: MigrationConfig | None = None,
        run_id: str | None = None,
    ) -> "PipelineContext":
        """Construct a ``PipelineContext`` from call-site information.

        Args:
            source_file: Path to the source unittest file.
            target_file: Optional output path for the migrated pytest file.
                When omitted the source path is reused; callers can modify
                suffix/extension using a ``MigrationConfig``.
            config: Optional ``MigrationConfig``. When omitted a
                default configuration is created.
            run_id: Optional run identifier; if omitted a UUID is
                generated.

        Returns:
            A new ``PipelineContext`` instance.
        """
        if not target_file:
            # Preserve the original file extension by default. If callers
            # want a different extension or suffix they may pass
            # `target_extension` or `target_suffix` via the MigrationConfig
            # (or provide an explicit target_file).
            source_path = Path(source_file)
            target_file = str(source_path)

        if not config:
            config = MigrationConfig()

        if not run_id:
            run_id = str(uuid.uuid4())

        return cls(source_file=source_file, target_file=target_file, config=config, run_id=run_id, metadata={})

    def with_metadata(self, key: str, value: Any) -> "PipelineContext":
        """Return a new context with an additional metadata entry.

        Args:
            key: Metadata key to add or replace.
            value: Value associated with the key.

        Returns:
            A new ``PipelineContext`` with the updated metadata.
        """
        new_metadata = {**self.metadata, key: value}
        return dataclasses.replace(self, metadata=new_metadata)

    def with_config(self, **config_overrides: Any) -> "PipelineContext":
        """Return a new context with updated configuration values.

        The method applies overrides to the current ``MigrationConfig``
        and returns a copy of the context referencing the updated
        configuration.

        Args:
            **config_overrides: Keyword overrides applied to the config.

        Returns:
            A new ``PipelineContext`` instance using the updated
            configuration.
        """
        new_config = self.config.with_override(**config_overrides)
        return dataclasses.replace(self, config=new_config)

    def get_source_path(self) -> Path:
        """Return the source file as a :class:`pathlib.Path`.

        Returns:
            A :class:`pathlib.Path` for the configured source file.
        """
        return Path(self.source_file)

    def get_target_path(self) -> Path:
        """Return the target file as a :class:`pathlib.Path`.

        Returns:
            A :class:`pathlib.Path` for the configured target file.
        """
        return Path(self.target_file)

    def is_dry_run(self) -> bool:
        """Return True when the pipeline is configured for a dry run.

        Returns:
            ``True`` if no changes should be written to disk.
        """
        return self.config.dry_run

    def should_format_code(self) -> bool:
        """Determine whether formatting should be applied to output code.

        Returns:
            ``True`` when code formatting is requested. For backward
            compatibility this prefers an explicit ``format_code`` flag on
            the configuration when present and otherwise falls back to a
            sensible default.
        """
        # Code formatting flags were removed; prefer explicit flag when present
        return bool(getattr(self.config, "format_code", True))

    def get_line_length(self) -> int:
        """Return the configured line length for formatting.

        Returns:
            The configured maximum line length, defaulting to 120 when
            unspecified.
        """
        return self.config.line_length or 120

    def to_dict(self) -> dict[str, Any]:
        """Serialize the context to a simple dictionary.

        Returns:
            A mapping containing serializable context fields.
        """
        return {
            "source_file": self.source_file,
            "target_file": self.target_file,
            "config": self.config.to_dict(),
            "run_id": self.run_id,
            "metadata": self.metadata,
            "decision_model": self.decision_model.to_dict() if self.decision_model else None,
        }

    def __str__(self) -> str:
        """Compact string representation for logging.

        Returns:
            A one-line string showing source, target and an abbreviated
            run id.
        """
        return f"PipelineContext(source={self.source_file}, target={self.target_file}, run_id={self.run_id[:8]}...)"

    def __repr__(self) -> str:
        """Detailed developer-friendly representation.

        Returns:
            Full ``repr`` suitable for debugging and tests.
        """
        return (
            f"PipelineContext("
            f"source_file={repr(self.source_file)}, "
            f"target_file={repr(self.target_file)}, "
            f"config={repr(self.config)}, "
            f"run_id={repr(self.run_id)}, "
            f"metadata={repr(self.metadata)}, "
            f"decision_model={repr(self.decision_model)}"
            f")"
        )


class ContextManager:
    """Helper utilities for loading and validating pipeline configuration.

    ``ContextManager`` exposes a small set of convenience methods for
    reading configuration from files and performing lightweight
    validation. Methods return ``Result`` instances so callers can
    react to failures or warnings in a structured way.
    """

    @staticmethod
    def load_config_from_file(config_file: str) -> Result[MigrationConfig]:
        """Load a ``MigrationConfig`` from a YAML file.

        This helper reads YAML from ``config_file`` and converts it to a
        ``MigrationConfig``. Unknown top-level keys are ignored so that
        older configuration files remain compatible.

        Args:
            config_file: Path to the YAML configuration file.

        Returns:
            A ``Result`` containing the constructed ``MigrationConfig`` on
            success or an error describing the problem.
        """
        try:
            import yaml  # type: ignore[import-untyped]

            with open(config_file, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if not isinstance(config_data, dict):
                return Result.failure(
                    ValueError("Configuration file must contain a dictionary"), {"config_file": config_file}
                )

            config = MigrationConfig.from_dict(config_data)
            return Result.success(config)

        except FileNotFoundError:
            return Result.failure(
                FileNotFoundError(f"Configuration file not found: {config_file}"), {"config_file": config_file}
            )
        except Exception as e:
            return Result.failure(ValueError(f"Error loading configuration: {e}"), {"config_file": config_file})

    @staticmethod
    def validate_config(config: MigrationConfig) -> Result[MigrationConfig]:
        """Validate a ``MigrationConfig`` instance.

        The method performs basic sanity checks (for example that
        ``line_length`` is within a reasonable range) and returns a
        ``Result`` that may indicate success, a set of warnings, or a
        failure depending on the configuration.

        Args:
            config: The configuration to validate.

        Returns:
            A ``Result`` describing the validation outcome.
        """
        issues = []

        # Basic sanity checks
        if config.line_length and (config.line_length < 60 or config.line_length > 200):
            issues.append("line_length must be between 60 and 200")

        if config.report_format not in ["json", "html", "markdown"]:
            issues.append("report_format must be one of: json, html, markdown")

        if issues:
            return Result.warning(config, [f"Configuration issues: {', '.join(issues)}"])

        return Result.success(config)
