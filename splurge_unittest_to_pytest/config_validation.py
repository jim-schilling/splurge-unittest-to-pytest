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
    assert_almost_equal_places: int = Field(
        default=7, ge=1, le=15, description="Default decimal places for assertAlmostEqual transformations"
    )
    log_level: str = Field(default="INFO", description="Default logging level")
    max_file_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum file size in MB")
    dry_run: bool = Field(default=False, description="Whether to perform a dry run")
    fail_fast: bool = Field(default=False, description="Whether to fail on first error")

    # Output formatting control
    format_output: bool = Field(default=True, description="Whether to format output code with black and isort")

    # Import handling options
    remove_unused_imports: bool = Field(default=True, description="Whether to remove unused unittest imports")
    preserve_import_comments: bool = Field(default=True, description="Whether to preserve comments in import sections")

    # Transform selection options
    transform_assertions: bool = Field(default=True, description="Whether to transform unittest assertions")
    transform_setup_teardown: bool = Field(default=True, description="Whether to convert setUp/tearDown methods")
    transform_subtests: bool = Field(default=True, description="Whether to attempt subTest conversions")
    transform_skip_decorators: bool = Field(default=True, description="Whether to convert skip decorators")
    transform_imports: bool = Field(default=True, description="Whether to transform unittest imports")

    # Processing options
    continue_on_error: bool = Field(default=False, description="Whether to continue on individual file errors")
    max_concurrent_files: int = Field(default=1, ge=1, le=50, description="Maximum concurrent file processing")
    cache_analysis_results: bool = Field(default=True, description="Whether to cache analysis results")

    # Advanced options
    preserve_file_encoding: bool = Field(default=True, description="Whether to preserve original file encoding")
    create_source_map: bool = Field(default=False, description="Whether to create source mapping for debugging")

    # Test method patterns
    test_method_prefixes: list[str] = Field(
        default_factory=lambda: ["test", "spec", "should", "it"], description="Prefixes for test methods"
    )

    # Parametrize settings
    parametrize: bool = Field(default=True, description="Whether to convert subTests to parametrize")
    parametrize_ids: bool = Field(default=False, description="Whether to add ids to parametrize")
    parametrize_type_hints: bool = Field(default=False, description="Whether to add type hints to parametrize")

    # Degradation settings
    degradation_enabled: bool = Field(
        default=True, description="Whether to enable degradation for failed transformations"
    )
    degradation_tier: str = Field(
        default="advanced", description="Degradation tier (essential, advanced, experimental)"
    )

    @field_validator("file_patterns")
    @classmethod
    def validate_file_patterns(cls, v):
        if not v:
            raise ValueError(
                "At least one file pattern must be specified. "
                "Use glob patterns like 'test_*.py', '*.py', or 'test_*.py' to match files."
            )

        # Validate each pattern with improved error messages
        for i, pattern in enumerate(v):
            if not isinstance(pattern, str):
                raise ValueError(f"File pattern at index {i} must be a string, got {type(pattern).__name__}")

            # Check for empty/whitespace-only patterns
            if not pattern or not pattern.strip():
                raise ValueError(
                    f"File pattern at index {i} cannot be empty or whitespace-only. "
                    "Use patterns like 'test_*.py', '*.py', or 'tests/**/*.py'."
                )

            # Check for basic pattern validity (should contain at least one wildcard or be a simple filename)
            if not any(char in pattern for char in ["*", "?", "["]) and not pattern.endswith(".py"):
                # Allow simple filenames that end with .py
                if not ("." in pattern and pattern.split(".")[-1].isalnum()):
                    raise ValueError(
                        f"File pattern '{pattern}' at index {i} should contain wildcards (*, ?, []) "
                        "or be a valid Python filename. Examples: 'test_*.py', '*.py', 'mytest.py'."
                    )
        return v

    @field_validator("test_method_prefixes")
    @classmethod
    def validate_test_prefixes(cls, v):
        if not v:
            raise ValueError(
                "At least one test method prefix must be specified. "
                "Common prefixes include 'test', 'spec', 'should', 'it'."
            )

        # Validate each prefix with improved error messages
        for i, prefix in enumerate(v):
            if not isinstance(prefix, str):
                raise ValueError(f"Test method prefix at index {i} must be a string, got {type(prefix).__name__}")

            # Check for empty/whitespace-only prefixes
            if not prefix or not prefix.strip():
                raise ValueError(
                    f"Test method prefix at index {i} cannot be empty or whitespace-only. "
                    "Use meaningful prefixes like 'test', 'spec', or 'should'."
                )

            # Check for reasonable prefix format (letters, numbers, underscores, hyphens)
            if not prefix.replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    f"Test method prefix '{prefix}' at index {i} contains invalid characters. "
                    "Use only letters, numbers, underscores, and hyphens. "
                    "Examples: 'test', 'test_case', 'should_pass'."
                )

        return v

    @field_validator("assert_almost_equal_places")
    @classmethod
    def validate_assert_places(cls, v):
        if not isinstance(v, int):
            raise ValueError("assert_almost_equal_places must be an integer (1-15)")

        if v < 1 or v > 15:
            raise ValueError(
                f"assert_almost_equal_places must be between 1 and 15, got {v}. "
                "Use 7 for standard precision, or 1-3 for high precision floating point comparisons. "
                "Higher values (10-15) are useful for very precise decimal comparisons."
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if not isinstance(v, str):
            raise ValueError("log_level must be a string (DEBUG, INFO, WARNING, ERROR)")

        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(
                f"log_level must be one of: {', '.join(valid_levels)}, got '{v}'. "
                "Choose DEBUG for detailed troubleshooting, INFO for normal operation, "
                "WARNING for important messages, or ERROR for critical issues only."
            )
        return upper_v

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
