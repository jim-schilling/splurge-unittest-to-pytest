"""Configuration validation using pydantic schemas.

This module provides runtime validation for all configuration objects
to ensure they are properly formed and contain valid values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic import BaseModel, Field, field_validator
    from pydantic import ValidationError as PydanticValidationError
else:
    try:
        from pydantic import BaseModel, Field, field_validator
        from pydantic import ValidationError as PydanticValidationError
    except ImportError:
        # Fallback if pydantic is not available
        class BaseModel:
            def __init__(self, **data):
                for key, value in data.items():
                    setattr(self, key, value)

        class Field:
            def __init__(self, default=None, **kwargs):
                self.default = default

        class ValidationError(ValueError):
            pass

        def field_validator(*args, **kwargs):
            def decorator(func):
                return func

            return decorator


class ValidatedMigrationConfig(BaseModel):
    """Validated version of MigrationConfig with runtime validation."""

    # Output settings
    target_root: str | None = Field(default=None, description="Root directory for output files")
    root_directory: str | None = Field(default=None, description="Root directory for source files")
    file_patterns: list[str] = Field(default_factory=lambda: ["test_*.py"], description="File patterns to match")
    recurse_directories: bool = Field(default=True, description="Whether to recurse into subdirectories")
    backup_originals: bool = Field(default=True, description="Whether to backup original files")
    backup_root: str | None = Field(default=None, description="Root directory for backups")
    target_suffix: str = Field(default="", description="Suffix to append to target filenames")
    target_extension: str | None = Field(default=None, description="Extension for target files")

    # Transformation settings
    line_length: int | None = Field(default=120, ge=60, le=200, description="Maximum line length")
    dry_run: bool = Field(default=False, description="Whether to perform a dry run")
    fail_fast: bool = Field(default=False, description="Whether to fail on first error")

    # Test method patterns
    test_method_prefixes: list[str] = Field(default_factory=lambda: ["test"], description="Prefixes for test methods")

    # Parametrize settings
    parametrize: bool = Field(default=True, description="Whether to convert subTests to parametrize")
    parametrize_ids: bool = Field(default=False, description="Whether to add ids to parametrize")
    parametrize_type_hints: bool = Field(default=False, description="Whether to add type hints to parametrize")

    @field_validator("file_patterns")
    @classmethod
    def validate_file_patterns(cls, v):
        if not v:
            raise ValueError("At least one file pattern must be specified")
        for pattern in v:
            if not isinstance(pattern, str) or not pattern.strip():
                raise ValueError(f"Invalid file pattern: {pattern}")
        return v

    @field_validator("test_method_prefixes")
    @classmethod
    def validate_test_prefixes(cls, v):
        if not v:
            raise ValueError("At least one test method prefix must be specified")
        for prefix in v:
            if not isinstance(prefix, str) or not prefix.strip():
                raise ValueError(f"Invalid test method prefix: {prefix}")
        return v

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        arbitrary_types_allowed = True


def validate_migration_config(config_dict: dict[str, Any]) -> ValidatedMigrationConfig:
    """Validate a migration configuration dictionary.

    Args:
        config_dict: Configuration dictionary to validate

    Returns:
        Validated configuration object

    Raises:
        ValidationError: If configuration is invalid
    """
    try:
        return ValidatedMigrationConfig(**config_dict)
    except PydanticValidationError as e:
        from .exceptions import ValidationError

        raise ValidationError(f"Invalid migration configuration: {e}", validation_type="configuration") from e


def validate_migration_config_object(config) -> ValidatedMigrationConfig:
    """Validate an existing MigrationConfig object by converting to dict and back.

    Args:
        config: MigrationConfig object to validate

    Returns:
        Validated configuration object

    Raises:
        ValidationError: If configuration is invalid
    """
    # Convert config object to dict for validation
    config_dict = {}
    if hasattr(config, "__dict__"):
        config_dict = config.__dict__.copy()
    elif hasattr(config, "__annotations__"):
        # Try to get attributes from annotations
        for attr in getattr(config, "__annotations__", {}):
            if hasattr(config, attr):
                config_dict[attr] = getattr(config, attr)

    return validate_migration_config(config_dict)


def create_validated_config(**kwargs) -> ValidatedMigrationConfig:
    """Create a validated configuration object from keyword arguments.

    Args:
        **kwargs: Configuration parameters

    Returns:
        Validated configuration object

    Raises:
        ValidationError: If configuration is invalid
    """
    return ValidatedMigrationConfig(**kwargs)
