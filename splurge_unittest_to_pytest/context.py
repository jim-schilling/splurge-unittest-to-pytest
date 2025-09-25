"""Pipeline context and configuration management.

This module provides immutable context objects that are threaded through
the entire pipeline execution, along with configuration management.
"""

import dataclasses
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .result import Result


class FixtureScope(Enum):
    """Scope for pytest fixtures."""

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    SESSION = "session"


class AssertionType(Enum):
    """Types of test assertions."""

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
    """Migration behavior configuration."""

    # Output settings
    target_directory: str | None = None
    preserve_structure: bool = True
    backup_originals: bool = True

    # Transformation settings
    convert_classes_to_functions: bool = True
    merge_setup_teardown: bool = True
    generate_fixtures: bool = True
    fixture_scope: FixtureScope = FixtureScope.FUNCTION

    # Code quality settings
    format_code: bool = True
    optimize_imports: bool = True
    add_type_hints: bool = False
    line_length: int | None = 120  # Use black default (120) if None

    # Behavior settings
    dry_run: bool = False
    fail_fast: bool = False
    parallel_processing: bool = True
    max_workers: int = 4

    # Reporting settings
    verbose: bool = False
    generate_report: bool = True
    report_format: str = "json"  # json, html, markdown

    def with_override(self, **kwargs: Any) -> "MigrationConfig":
        """Create new config with overrides.

        Args:
            **kwargs: Configuration values to override

        Returns:
            New MigrationConfig with overridden values
        """
        return dataclasses.replace(self, **kwargs)

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "MigrationConfig":
        """Create config from dictionary.

        Args:
            config_dict: Dictionary containing configuration values

        Returns:
            New MigrationConfig instance
        """
        # Handle enum conversions
        if "fixture_scope" in config_dict and isinstance(config_dict["fixture_scope"], str):
            config_dict["fixture_scope"] = FixtureScope(config_dict["fixture_scope"])

        return cls(**config_dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Dictionary representation of config
        """
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class PipelineContext:
    """Immutable execution context passed through entire pipeline execution."""

    source_file: str
    target_file: str
    config: MigrationConfig
    run_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate context consistency."""
        if not Path(self.source_file).exists():
            raise ValueError(f"Source file does not exist: {self.source_file}")

    @classmethod
    def create(
        cls,
        source_file: str,
        target_file: str | None = None,
        config: MigrationConfig | None = None,
        run_id: str | None = None,
    ) -> "PipelineContext":
        """Create new pipeline context.

        Args:
            source_file: Path to source unittest file
            target_file: Path for output pytest file (optional)
            config: Migration configuration (optional)
            run_id: Unique run identifier (optional)

        Returns:
            New PipelineContext instance
        """
        if not target_file:
            source_path = Path(source_file)
            target_file = str(source_path.with_suffix(".pytest.py"))

        if not config:
            config = MigrationConfig()

        if not run_id:
            run_id = str(uuid.uuid4())

        return cls(source_file=source_file, target_file=target_file, config=config, run_id=run_id, metadata={})

    def with_metadata(self, key: str, value: Any) -> "PipelineContext":
        """Return new context with additional metadata.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            New PipelineContext with added metadata
        """
        new_metadata = {**self.metadata, key: value}
        return dataclasses.replace(self, metadata=new_metadata)

    def with_config(self, **config_overrides: Any) -> "PipelineContext":
        """Return new context with updated configuration.

        Args:
            **config_overrides: Configuration values to override

        Returns:
            New PipelineContext with updated config
        """
        new_config = self.config.with_override(**config_overrides)
        return dataclasses.replace(self, config=new_config)

    def get_source_path(self) -> Path:
        """Get source file as Path object.

        Returns:
            Source file path
        """
        return Path(self.source_file)

    def get_target_path(self) -> Path:
        """Get target file as Path object.

        Returns:
            Target file path
        """
        return Path(self.target_file)

    def is_dry_run(self) -> bool:
        """Check if this is a dry run.

        Returns:
            True if dry run mode is enabled
        """
        return self.config.dry_run

    def should_format_code(self) -> bool:
        """Check if code formatting should be applied.

        Returns:
            True if code formatting is enabled
        """
        return self.config.format_code

    def get_line_length(self) -> int:
        """Get configured line length.

        Returns:
            Line length for formatting
        """
        return self.config.line_length or 120

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary representation.

        Returns:
            Dictionary representation of the context
        """
        return {
            "source_file": self.source_file,
            "target_file": self.target_file,
            "config": self.config.to_dict(),
            "run_id": self.run_id,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation of the context."""
        return f"PipelineContext(source={self.source_file}, target={self.target_file}, run_id={self.run_id[:8]}...)"

    def __repr__(self) -> str:
        """Detailed string representation of the context."""
        return (
            f"PipelineContext("
            f"source_file={repr(self.source_file)}, "
            f"target_file={repr(self.target_file)}, "
            f"config={repr(self.config)}, "
            f"run_id={repr(self.run_id)}, "
            f"metadata={repr(self.metadata)}"
            f")"
        )


class ContextManager:
    """Utility class for managing pipeline contexts."""

    @staticmethod
    def load_config_from_file(config_file: str) -> Result[MigrationConfig]:
        """Load configuration from file.

        Args:
            config_file: Path to configuration file

        Returns:
            Result containing loaded configuration or error
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
        """Validate configuration values.

        Args:
            config: Configuration to validate

        Returns:
            Result containing validated configuration or error
        """
        issues = []

        if config.max_workers < 1:
            issues.append("max_workers must be at least 1")

        if config.line_length and (config.line_length < 60 or config.line_length > 200):
            issues.append("line_length must be between 60 and 200")

        if config.report_format not in ["json", "html", "markdown"]:
            issues.append("report_format must be one of: json, html, markdown")

        if issues:
            return Result.warning(config, [f"Configuration issues: {', '.join(issues)}"])

        return Result.success(config)
