"""Configuration validation using pydantic schemas.

This module provides runtime validation for all configuration objects
to ensure they are properly formed and contain valid values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    from typing import Self  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import Self

if TYPE_CHECKING:
    from pydantic import BaseModel, Field, field_validator, model_validator
    from pydantic import ValidationError as PydanticValidationError
else:
    try:
        from pydantic import BaseModel, Field, field_validator, model_validator
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

        def model_validator(*args, **kwargs):
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
    max_depth: int = Field(
        default=7, ge=3, le=15, description="Maximum depth to traverse nested control flow structures"
    )

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

    @model_validator(mode="after")
    def validate_cross_field_compatibility(self) -> Self:
        """Validate combinations of configuration options for compatibility."""
        errors = []

        # Dry run with target_root - dry run ignores target_root
        if self.dry_run and self.target_root:
            errors.append(
                {
                    "field": "dry_run",
                    "message": "dry_run mode ignores target_root setting",
                    "suggestion": "Remove target_root or set dry_run=False",
                }
            )

        # Backup root without backups enabled
        if self.backup_root and not self.backup_originals:
            errors.append(
                {
                    "field": "backup_root",
                    "message": "backup_root specified but backup_originals is disabled",
                    "suggestion": "Enable backup_originals or remove backup_root",
                }
            )

        # Large file size warning - performance impact
        if self.max_file_size_mb > 50:
            errors.append(
                {
                    "field": "max_file_size_mb",
                    "message": "Large file size limit may impact memory usage and performance",
                    "suggestion": "Consider reducing max_file_size_mb for better performance. Use 10-20MB for typical use cases.",
                }
            )

        # Experimental degradation tier without dry run - safety concern
        if self.degradation_tier == "experimental" and not self.dry_run:
            errors.append(
                {
                    "field": "degradation_tier",
                    "message": "Experimental degradation tier without dry_run may cause unexpected results",
                    "suggestion": "Use dry_run=True when using experimental features, or consider advanced tier for safer operation.",
                }
            )

        if errors:
            error_messages = []
            for error in errors:
                error_messages.append(f"{error['field']}: {error['message']} - {error['suggestion']}")
            raise ValueError(f"Configuration conflicts detected: {'; '.join(error_messages)}")

        return self

    @field_validator("target_root")
    @classmethod
    def validate_target_root(cls, v):
        """Validate target_root directory exists and is writable."""
        if v is None:
            return v

        if not isinstance(v, str):
            raise ValueError("target_root must be a string path")

        path = Path(v)
        if not path.exists():
            # For dry run, we don't need to create the directory, just warn
            return v

        if not path.is_dir():
            raise ValueError(f"target_root must be a directory, got: {v}")

        # Check if directory is writable
        try:
            # Try to create a test file to check write permissions
            test_file = path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
        except (OSError, PermissionError) as e:
            raise ValueError(f"target_root directory is not writable: {v}. Error: {e}") from e

        return v

    @field_validator("backup_root")
    @classmethod
    def validate_backup_root(cls, v):
        """Validate backup_root directory exists and is writable."""
        if v is None:
            return v

        if not isinstance(v, str):
            raise ValueError("backup_root must be a string path")

        path = Path(v)
        if not path.exists():
            # For dry run, we don't need to create the directory, just warn
            return v

        if not path.is_dir():
            raise ValueError(f"backup_root must be a directory, got: {v}")

        # Check if directory is writable
        try:
            # Try to create a test file to check write permissions
            test_file = path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
        except (OSError, PermissionError) as e:
            raise ValueError(f"backup_root directory is not writable: {v}. Error: {e}") from e

        return v

    @field_validator("degradation_tier")
    @classmethod
    def validate_degradation_tier(cls, v):
        """Validate degradation tier values."""
        valid_tiers = ["essential", "advanced", "experimental"]
        if v not in valid_tiers:
            raise ValueError(
                f"degradation_tier must be one of: {', '.join(valid_tiers)}, got '{v}'. "
                "Choose 'essential' for basic transformations only, 'advanced' for comprehensive transformations, "
                "or 'experimental' for cutting-edge features with higher risk."
            )
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


class ConfigurationProfile:
    """Enumeration of detected configuration use case profiles."""

    BASIC_MIGRATION = "basic_migration"
    CUSTOM_TESTING_FRAMEWORK = "custom_testing_framework"
    ENTERPRISE_DEPLOYMENT = "enterprise_deployment"
    CI_INTEGRATION = "ci_integration"
    DEVELOPMENT_DEBUGGING = "development_debugging"
    PRODUCTION_DEPLOYMENT = "production_deployment"
    UNKNOWN = "unknown"


class ConfigurationUseCaseDetector:
    """Detects intended use case from configuration patterns."""

    def __init__(self):
        self._patterns = {
            ConfigurationProfile.BASIC_MIGRATION: self._matches_basic_migration,
            ConfigurationProfile.CUSTOM_TESTING_FRAMEWORK: self._matches_custom_framework,
            ConfigurationProfile.ENTERPRISE_DEPLOYMENT: self._matches_enterprise_setup,
            ConfigurationProfile.CI_INTEGRATION: self._matches_ci_integration,
            ConfigurationProfile.DEVELOPMENT_DEBUGGING: self._matches_development_debugging,
            ConfigurationProfile.PRODUCTION_DEPLOYMENT: self._matches_production_deployment,
        }

    def detect_use_case(self, config: ValidatedMigrationConfig) -> str:
        """Detect the intended use case from configuration.

        Args:
            config: Validated configuration object

        Returns:
            Detected use case profile
        """
        # Score each pattern and return the highest scoring one
        scores: dict[str, float] = {}

        for profile, matcher in self._patterns.items():
            try:
                score = matcher(config)
                if score > 0:
                    scores[profile] = score
            except Exception:
                # If pattern matching fails, give it a score of 0
                scores[profile] = 0

        if not scores:
            return ConfigurationProfile.UNKNOWN

        # Return the profile with the highest score
        return max(scores, key=lambda k: scores[k])

    def _matches_basic_migration(self, config: ValidatedMigrationConfig) -> float:
        """Check if configuration matches basic migration pattern."""
        score = 0.0

        # Basic patterns: default file patterns, recurse directories, default settings
        if config.file_patterns == ["test_*.py"]:
            score += 0.5
        if config.recurse_directories:
            score += 0.2
        if config.backup_originals:
            score += 0.1
        if config.dry_run:
            score += 0.1
        if config.degradation_tier == "advanced":
            score += 0.2
        if config.max_file_size_mb <= 20:
            score += 0.1

        # Penalize if using custom prefixes (indicates custom framework)
        if len(config.test_method_prefixes) > 4:
            score -= 0.3
        if any(prefix in config.test_method_prefixes for prefix in ["spec", "should", "it", "feature"]):
            score -= 0.2

        return max(0.0, score)  # Don't return negative scores

    def _matches_custom_framework(self, config: ValidatedMigrationConfig) -> float:
        """Check if configuration matches custom testing framework pattern."""
        score = 0.0

        # Custom patterns: multiple test prefixes beyond defaults, specific patterns
        default_prefixes = ["test", "spec", "should", "it"]  # Default prefixes
        extra_prefixes = [p for p in config.test_method_prefixes if p not in default_prefixes]

        if len(extra_prefixes) > 0:
            score += 0.3 * len(extra_prefixes)  # Score for each extra prefix

        # Boost score for clearly custom prefixes
        custom_indicators = ["feature", "scenario", "describe", "context"]
        if any(prefix in config.test_method_prefixes for prefix in custom_indicators):
            score += 0.3

        if config.degradation_tier == "advanced":
            score += 0.1

        return score

    def _matches_enterprise_setup(self, config: ValidatedMigrationConfig) -> float:
        """Check if configuration matches enterprise deployment pattern."""
        score = 0.0

        # Enterprise patterns: backup root, specific target structure, fail fast
        if config.backup_root:
            score += 0.4  # Increased weight
        if config.target_root:
            score += 0.3  # Increased weight
        if config.fail_fast:
            score += 0.3  # Increased weight
        if config.backup_originals:
            score += 0.2  # Enterprise typically wants backups
        if config.max_concurrent_files > 1:
            score += 0.2  # Enterprise may want concurrent processing

        # Penalize if using basic patterns
        if config.file_patterns == ["test_*.py"]:
            score -= 0.1  # Less likely to be enterprise if using basic patterns
        if not config.dry_run:
            score += 0.1  # Enterprise more likely to run actual migrations

        return max(0.0, score)

    def _matches_ci_integration(self, config: ValidatedMigrationConfig) -> float:
        """Check if configuration matches CI integration pattern."""
        score = 0.0

        # CI patterns: no dry run, fail fast, concurrent processing, specific patterns
        if not config.dry_run:
            score += 0.3
        if config.fail_fast:
            score += 0.3
        if config.max_concurrent_files > 1:
            score += 0.2
        if config.cache_analysis_results:
            score += 0.1
        if config.max_file_size_mb <= 20:
            score += 0.1

        return score

    def _matches_development_debugging(self, config: ValidatedMigrationConfig) -> float:
        """Check if configuration matches development debugging pattern."""
        score = 0.0

        # Debug patterns: dry run, verbose logging, debug level, small file size
        if config.dry_run:
            score += 0.4  # Increased weight
        if config.log_level == "DEBUG":
            score += 0.4  # Increased weight
        if config.max_file_size_mb <= 5:
            score += 0.3  # Increased weight
        if config.create_source_map:
            score += 0.3  # Increased weight

        # Penalize if using production-like patterns
        if not config.dry_run:
            score -= 0.2  # Less likely to be development if not using dry run
        if config.fail_fast:
            score -= 0.1  # Development usually doesn't use fail fast
        if config.degradation_tier == "essential":
            score -= 0.1  # Development usually wants more features

        return max(0.0, score)

    def _matches_production_deployment(self, config: ValidatedMigrationConfig) -> float:
        """Check if configuration matches production deployment pattern."""
        score = 0.0

        # Production patterns: no dry run, fail fast, conservative settings
        if not config.dry_run:
            score += 0.2
        if config.fail_fast:
            score += 0.3
        if config.degradation_tier == "essential":
            score += 0.3
        if config.backup_originals:
            score += 0.2

        return score


def detect_configuration_use_case(config: ValidatedMigrationConfig) -> str:
    """Convenience function to detect configuration use case.

    Args:
        config: Validated configuration object

    Returns:
        Detected use case profile
    """
    detector = ConfigurationUseCaseDetector()
    return detector.detect_use_case(config)


class SuggestionType(Enum):
    """Types of configuration suggestions."""

    CORRECTION = "correction"  # Fix configuration errors
    ACTION = "action"  # Recommended actions
    PERFORMANCE = "performance"  # Performance optimizations
    SAFETY = "safety"  # Safety recommendations
    OPTIMIZATION = "optimization"  # General optimizations


@dataclass
class Suggestion:
    """A configuration suggestion with rich metadata."""

    type: SuggestionType
    message: str
    action: str
    examples: list[str] | None = None
    priority: int = 1  # Higher numbers = higher priority

    def __str__(self) -> str:
        return f"[{self.type.value.upper()}] {self.message} - {self.action}"


class ConfigurationAdvisor:
    """Provides intelligent configuration suggestions based on use case detection."""

    def __init__(self):
        self.use_case_detector = ConfigurationUseCaseDetector()

    def suggest_improvements(self, config: ValidatedMigrationConfig) -> list[Suggestion]:
        """Generate context-aware improvement suggestions.

        Args:
            config: Validated configuration object

        Returns:
            List of configuration suggestions
        """
        suggestions = []

        # Get detected use case
        use_case = self.use_case_detector.detect_use_case(config)

        # Performance suggestions based on configuration
        suggestions.extend(self._generate_performance_suggestions(config))

        # Safety recommendations based on configuration
        suggestions.extend(self._generate_safety_suggestions(config))

        # Use case specific suggestions
        suggestions.extend(self._generate_use_case_suggestions(config, use_case))

        # General optimization suggestions
        suggestions.extend(self._generate_optimization_suggestions(config))

        # Sort by priority and return top suggestions
        suggestions.sort(key=lambda s: s.priority, reverse=True)
        return suggestions[:10]  # Return top 10 suggestions

    def _generate_performance_suggestions(self, config: ValidatedMigrationConfig) -> list[Suggestion]:
        """Generate performance-related suggestions."""
        suggestions = []

        # Large file size warning
        if config.max_file_size_mb > 50:
            suggestions.append(
                Suggestion(
                    type=SuggestionType.PERFORMANCE,
                    message="Large file size limit may impact memory usage",
                    action="Consider reducing max_file_size_mb for better performance",
                    examples=["max_file_size_mb=20", "max_file_size_mb=10"],
                    priority=3,
                )
            )

        # Concurrent processing for large codebases
        if config.max_concurrent_files == 1 and config.max_file_size_mb > 20:
            suggestions.append(
                Suggestion(
                    type=SuggestionType.PERFORMANCE,
                    message="Enable concurrent processing for better performance",
                    action="Increase max_concurrent_files for large codebases",
                    examples=["max_concurrent_files=4", "max_concurrent_files=8"],
                    priority=2,
                )
            )

        return suggestions

    def _generate_safety_suggestions(self, config: ValidatedMigrationConfig) -> list[Suggestion]:
        """Generate safety-related suggestions."""
        suggestions = []

        # Experimental tier without dry run
        if config.degradation_tier == "experimental" and not config.dry_run:
            suggestions.append(
                Suggestion(
                    type=SuggestionType.SAFETY,
                    message="Experimental tier without dry_run may cause unexpected results",
                    action="Use dry_run=True when using experimental features",
                    examples=["dry_run=True"],
                    priority=4,
                )
            )

        # No backups for production use
        if not config.backup_originals and not config.dry_run:
            suggestions.append(
                Suggestion(
                    type=SuggestionType.SAFETY,
                    message="No backups enabled - consider enabling for safety",
                    action="Enable backup_originals to preserve original files",
                    examples=["backup_originals=True"],
                    priority=2,
                )
            )

        return suggestions

    def _generate_use_case_suggestions(
        self, config: ValidatedMigrationConfig, use_case: str
    ) -> list[Suggestion]:
        """Generate use case specific suggestions."""
        suggestions = []

        if use_case == ConfigurationProfile.CI_INTEGRATION:
            suggestions.extend(
                [
                    Suggestion(
                        type=SuggestionType.PERFORMANCE,
                        message="Enable concurrent processing for faster CI runs",
                        action="Set max_concurrent_files to 4-8 for CI environments",
                        examples=["max_concurrent_files=4", "max_concurrent_files=8"],
                        priority=3,
                    ),
                    Suggestion(
                        type=SuggestionType.SAFETY,
                        message="Enable fail-fast for CI to catch issues early",
                        action="Set fail_fast=True to stop on first error",
                        examples=["fail_fast=True"],
                        priority=3,
                    ),
                ]
            )

        elif use_case == ConfigurationProfile.ENTERPRISE_DEPLOYMENT:
            suggestions.extend(
                [
                    Suggestion(
                        type=SuggestionType.OPTIMIZATION,
                        message="Use specific backup root for better organization",
                        action="Set backup_root to organize backups by project",
                        examples=["backup_root=./backups", "backup_root=/var/backups"],
                        priority=2,
                    ),
                    Suggestion(
                        type=SuggestionType.SAFETY,
                        message="Enable continue_on_error for robust enterprise deployment",
                        action="Set continue_on_error=True to process all files",
                        examples=["continue_on_error=True"],
                        priority=2,
                    ),
                ]
            )

        elif use_case == ConfigurationProfile.DEVELOPMENT_DEBUGGING:
            suggestions.extend(
                [
                    Suggestion(
                        type=SuggestionType.ACTION,
                        message="Enable source mapping for better debugging",
                        action="Set create_source_map=True for detailed transformation info",
                        examples=["create_source_map=True"],
                        priority=3,
                    ),
                    Suggestion(
                        type=SuggestionType.PERFORMANCE,
                        message="Use smaller file size limit for faster debugging",
                        action="Set max_file_size_mb=5 for quick iteration",
                        examples=["max_file_size_mb=5"],
                        priority=2,
                    ),
                ]
            )

        return suggestions

    def _generate_optimization_suggestions(self, config: ValidatedMigrationConfig) -> list[Suggestion]:
        """Generate general optimization suggestions."""
        suggestions = []

        # Cache analysis results for repeated runs
        if not config.cache_analysis_results and not config.dry_run:
            suggestions.append(
                Suggestion(
                    type=SuggestionType.OPTIMIZATION,
                    message="Enable analysis caching for repeated runs",
                    action="Set cache_analysis_results=True for better performance",
                    examples=["cache_analysis_results=True"],
                    priority=2,
                )
            )

        # Use appropriate line length for code style
        if config.line_length and config.line_length != 120:
            suggestions.append(
                Suggestion(
                    type=SuggestionType.OPTIMIZATION,
                    message="Consider using standard line length of 120",
                    action="Set line_length=120 for consistency with modern Python",
                    examples=["line_length=120"],
                    priority=1,
                )
            )

        return suggestions


def generate_configuration_suggestions(config: ValidatedMigrationConfig) -> list[Suggestion]:
    """Convenience function to generate configuration suggestions.

    Args:
        config: Validated configuration object

    Returns:
        List of configuration suggestions
    """
    advisor = ConfigurationAdvisor()
    return advisor.suggest_improvements(config)


@dataclass
class ConfigurationField:
    """Rich metadata for configuration fields."""

    name: str
    type: str
    description: str
    examples: list[str]
    constraints: list[str]
    related_fields: list[str]
    common_mistakes: list[str]
    category: str = "general"

    def get_help_text(self) -> str:
        """Generate comprehensive help text for this field."""
        lines = [f"**{self.name}** ({self.type})"]
        lines.append(f"{self.description}")
        lines.append("")

        if self.examples:
            lines.append("**Examples:**")
            for example in self.examples:
                lines.append(f"- `{example}`")
            lines.append("")

        if self.constraints:
            lines.append("**Constraints:**")
            for constraint in self.constraints:
                lines.append(f"- {constraint}")
            lines.append("")

        if self.common_mistakes:
            lines.append("**Common Mistakes:**")
            for mistake in self.common_mistakes:
                lines.append(f"- {mistake}")
            lines.append("")

        if self.related_fields:
            lines.append(f"**Related Fields:** {', '.join(self.related_fields)}")

        return "\n".join(lines)


class ConfigurationFieldRegistry:
    """Registry of configuration field metadata."""

    def __init__(self):
        self._fields = {}
        self._load_field_metadata()

    def _load_field_metadata(self):
        """Load metadata for all configuration fields."""
        self._fields = {
            "target_root": ConfigurationField(
                name="target_root",
                type="str | None",
                description="Root directory for output files",
                examples=["./output", "/tmp/migration", "./converted"],
                constraints=["Must be a valid directory path", "Directory must be writable"],
                related_fields=["backup_root", "target_suffix"],
                common_mistakes=[
                    "Using a file path instead of directory path",
                    "Using relative path that doesn't exist",
                    "Insufficient write permissions",
                ],
                category="output",
            ),
            "backup_root": ConfigurationField(
                name="backup_root",
                type="str | None",
                description="Root directory for backup files when recursing",
                examples=["./backups", "/var/backups", "./backup"],
                constraints=["Must be a valid directory path", "Directory must be writable"],
                related_fields=["backup_originals", "target_root"],
                common_mistakes=[
                    "Same as target_root (overwrites originals)",
                    "Non-existent directory",
                    "Insufficient write permissions",
                ],
                category="backup",
            ),
            "file_patterns": ConfigurationField(
                name="file_patterns",
                type="list[str]",
                description="Glob patterns to select files for migration",
                examples=["test_*.py", "*.py", "**/test_*.py", "tests/**/*.py"],
                constraints=["At least one pattern required", "Valid glob patterns only"],
                related_fields=["root_directory", "recurse_directories"],
                common_mistakes=[
                    "Empty list or no patterns",
                    "Invalid glob syntax",
                    "Too restrictive patterns missing files",
                ],
                category="input",
            ),
            "test_method_prefixes": ConfigurationField(
                name="test_method_prefixes",
                type="list[str]",
                description="Prefixes for test methods beyond the default 'test'",
                examples=["test", "spec", "should", "it", "test_case"],
                constraints=["At least one prefix required", "Valid identifier characters only"],
                related_fields=["detect_prefixes"],
                common_mistakes=["Empty list", "Invalid characters in prefixes", "Too many prefixes causing conflicts"],
                category="testing",
            ),
            "max_file_size_mb": ConfigurationField(
                name="max_file_size_mb",
                type="int",
                description="Maximum file size in MB to process",
                examples=["10", "20", "50", "100"],
                constraints=["1-100 MB range", "Larger files use more memory"],
                related_fields=["max_concurrent_files"],
                common_mistakes=[
                    "Setting too high (>50MB) causes memory issues",
                    "Setting too low (<5MB) for large codebases",
                ],
                category="performance",
            ),
            "degradation_tier": ConfigurationField(
                name="degradation_tier",
                type="str",
                description="Transformation complexity tier for robustness",
                examples=["essential", "advanced", "experimental"],
                constraints=["Must be one of: essential, advanced, experimental"],
                related_fields=["dry_run"],
                common_mistakes=[
                    "Using 'experimental' without dry_run",
                    "Using 'essential' for complex transformations",
                ],
                category="transformation",
            ),
            "line_length": ConfigurationField(
                name="line_length",
                type="int | None",
                description="Maximum line length used by formatters",
                examples=["88", "100", "120"],
                constraints=["60-200 characters", "None uses formatter default"],
                related_fields=["format_output"],
                common_mistakes=[
                    "Setting too low (<80) breaks code formatting",
                    "Setting too high (>120) reduces readability",
                ],
                category="formatting",
            ),
            "dry_run": ConfigurationField(
                name="dry_run",
                type="bool",
                description="Preview mode - shows output without writing files",
                examples=["true", "false"],
                constraints=["Boolean value only"],
                related_fields=["target_root", "backup_root"],
                common_mistakes=[
                    "Running production migrations without dry_run first",
                    "Expecting files to be written when dry_run=True",
                ],
                category="safety",
            ),
            "fail_fast": ConfigurationField(
                name="fail_fast",
                type="bool",
                description="Stop on first error instead of processing all files",
                examples=["true", "false"],
                constraints=["Boolean value only"],
                related_fields=["continue_on_error"],
                common_mistakes=[
                    "Using fail_fast=false for CI (should be true)",
                    "Using fail_fast=true for development (should be false)",
                ],
                category="error_handling",
            ),
            "backup_originals": ConfigurationField(
                name="backup_originals",
                type="bool",
                description="Create backup copies of original files before writing",
                examples=["true", "false"],
                constraints=["Boolean value only"],
                related_fields=["backup_root"],
                common_mistakes=[
                    "Disabling backups for production use",
                    "Setting backup_root without enabling backups",
                ],
                category="backup",
            ),
        }

    def get_field(self, name: str) -> ConfigurationField | None:
        """Get metadata for a specific field."""
        return self._fields.get(name)

    def get_all_fields(self) -> dict[str, ConfigurationField]:
        """Get metadata for all fields."""
        return self._fields.copy()

    def get_fields_by_category(self, category: str) -> dict[str, ConfigurationField]:
        """Get fields belonging to a specific category."""
        return {name: field for name, field in self._fields.items() if field.category == category}

    def generate_help_text(self, field_name: str) -> str:
        """Generate comprehensive help text for a field."""
        field = self.get_field(field_name)
        if field:
            return field.get_help_text()
        return f"No documentation available for field: {field_name}"


# Global registry instance
_field_registry = ConfigurationFieldRegistry()


def get_configuration_field_registry() -> ConfigurationFieldRegistry:
    """Get the global configuration field registry."""
    return _field_registry


def get_field_help(field_name: str) -> str:
    """Convenience function to get help for a specific field."""
    return _field_registry.generate_help_text(field_name)


def generate_configuration_documentation(format: str = "markdown") -> str:
    """Generate comprehensive configuration documentation from field metadata.

    Args:
        format: Output format ("markdown" or "html")

    Returns:
        Complete configuration documentation
    """
    registry = get_configuration_field_registry()

    if format == "markdown":
        return _generate_markdown_documentation(registry)
    elif format == "html":
        return _generate_html_documentation(registry)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'markdown' or 'html'.")


def _generate_markdown_documentation(registry: ConfigurationFieldRegistry) -> str:
    """Generate Markdown documentation for all configuration fields."""
    lines = []

    lines.append("# Configuration Reference")
    lines.append("")
    lines.append(
        "This document provides comprehensive information about all configuration options available in splurge-unittest-to-pytest."
    )
    lines.append("")

    # Group fields by category
    categories: dict[str, list[ConfigurationField]] = {}
    for _field_name, field in registry.get_all_fields().items():
        category = field.category
        if category not in categories:
            categories[category] = []
        categories[category].append(field)

    # Sort categories for consistent output
    category_order = [
        "input",
        "output",
        "backup",
        "testing",
        "transformation",
        "performance",
        "formatting",
        "safety",
        "error_handling",
    ]
    sorted_categories = sorted(
        categories.keys(), key=lambda x: category_order.index(x) if x in category_order else len(category_order)
    )

    for category in sorted_categories:
        fields = categories[category]
        # Sort fields alphabetically within category
        fields.sort(key=lambda f: f.name)

        lines.append(f"## {category.title()} Configuration")
        lines.append("")

        for field in fields:
            lines.append(field.get_help_text())
            lines.append("")

    return "\n".join(lines)


def _generate_html_documentation(registry: ConfigurationFieldRegistry) -> str:
    """Generate HTML documentation for all configuration fields."""
    lines = []

    lines.append("<!DOCTYPE html>")
    lines.append("<html>")
    lines.append("<head>")
    lines.append("    <title>splurge-unittest-to-pytest Configuration Reference</title>")
    lines.append("    <style>")
    lines.append("        body { font-family: Arial, sans-serif; margin: 40px; }")
    lines.append("        .field { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }")
    lines.append("        .field-name { font-size: 1.2em; font-weight: bold; color: #2c3e50; }")
    lines.append("        .field-type { color: #7f8c8d; font-family: monospace; }")
    lines.append("        .field-description { margin: 10px 0; }")
    lines.append("        .examples, .constraints, .mistakes { margin: 10px 0; }")
    lines.append("        .examples ul, .constraints ul, .mistakes ul { margin: 5px 0; padding-left: 20px; }")
    lines.append("        .related-fields { font-style: italic; color: #34495e; }")
    lines.append(
        "        .category { font-size: 1.5em; margin: 40px 0 20px 0; color: #2980b9; border-bottom: 2px solid #2980b9; }"
    )
    lines.append("    </style>")
    lines.append("</head>")
    lines.append("<body>")
    lines.append("    <h1>splurge-unittest-to-pytest Configuration Reference</h1>")
    lines.append(
        "    <p>This document provides comprehensive information about all configuration options available in splurge-unittest-to-pytest.</p>"
    )

    # Group fields by category
    categories: dict[str, list[ConfigurationField]] = {}
    for _field_name, field in registry.get_all_fields().items():
        category = field.category
        if category not in categories:
            categories[category] = []
        categories[category].append(field)

    # Sort categories for consistent output
    category_order = [
        "input",
        "output",
        "backup",
        "testing",
        "transformation",
        "performance",
        "formatting",
        "safety",
        "error_handling",
    ]
    sorted_categories = sorted(
        categories.keys(), key=lambda x: category_order.index(x) if x in category_order else len(category_order)
    )

    for category in sorted_categories:
        fields = categories[category]
        # Sort fields alphabetically within category
        fields.sort(key=lambda f: f.name)

        lines.append(f'    <h2 class="category">{category.title()} Configuration</h2>')

        for field in fields:
            lines.append('    <div class="field">')
            lines.append(
                f'        <div class="field-name">{field.name} <span class="field-type">({field.type})</span></div>'
            )
            lines.append(f'        <div class="field-description">{field.description}</div>')

            if field.examples:
                lines.append('        <div class="examples">')
                lines.append("            <strong>Examples:</strong>")
                lines.append("            <ul>")
                for example in field.examples:
                    lines.append(f"                <li><code>{example}</code></li>")
                lines.append("            </ul>")
                lines.append("        </div>")

            if field.constraints:
                lines.append('        <div class="constraints">')
                lines.append("            <strong>Constraints:</strong>")
                lines.append("            <ul>")
                for constraint in field.constraints:
                    lines.append(f"                <li>{constraint}</li>")
                lines.append("            </ul>")
                lines.append("        </div>")

            if field.common_mistakes:
                lines.append('        <div class="mistakes">')
                lines.append("            <strong>Common Mistakes:</strong>")
                lines.append("            <ul>")
                for mistake in field.common_mistakes:
                    lines.append(f"                <li>{mistake}</li>")
                lines.append("            </ul>")
                lines.append("        </div>")

            if field.related_fields:
                lines.append(
                    f'        <div class="related-fields">Related Fields: {", ".join(field.related_fields)}</div>'
                )

            lines.append("    </div>")

    lines.append("</body>")
    lines.append("</html>")

    return "\n".join(lines)


class ConfigurationTemplate:
    """A configuration template for a specific use case."""

    def __init__(self, name: str, description: str, config_dict: dict, use_case: str):
        self.name = name
        self.description = description
        self.config_dict = config_dict
        self.use_case = use_case

    def to_yaml(self) -> str:
        """Convert template to YAML format."""
        import yaml  # type: ignore[import-untyped]

        # Create a comment header
        header = f"# {self.name}\n# {self.description}\n\n"
        yaml_content = yaml.dump(self.config_dict, default_flow_style=False, indent=2)

        return header + yaml_content

    def to_cli_args(self) -> str:
        """Convert template to CLI arguments."""
        args = []
        for key, value in self.config_dict.items():
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key.replace('_', '-')}")
            elif isinstance(value, list):
                for item in value:
                    args.append(f"--{key.replace('_', '-')}={item}")
            elif value is not None:
                args.append(f"--{key.replace('_', '-')}={value}")

        return " ".join(args)


class ConfigurationTemplateManager:
    """Manages configuration templates for common use cases."""

    def __init__(self):
        self.templates = self._create_templates()

    def _create_templates(self) -> dict[str, ConfigurationTemplate]:
        """Create templates for common use cases."""
        return {
            "basic_migration": ConfigurationTemplate(
                name="Basic Migration",
                description="Standard unittest to pytest migration with safe defaults",
                config_dict={
                    "dry_run": True,
                    "backup_originals": True,
                    "file_patterns": ["test_*.py"],
                    "recurse_directories": True,
                    "degradation_tier": "advanced",
                    "max_file_size_mb": 20,
                    "format_output": True,
                    "remove_unused_imports": True,
                },
                use_case=ConfigurationProfile.BASIC_MIGRATION,
            ),
            "custom_framework": ConfigurationTemplate(
                name="Custom Testing Framework",
                description="Migration for projects using custom test method prefixes (BDD, RSpec style)",
                config_dict={
                    "test_method_prefixes": ["test", "spec", "should", "it"],
                    "detect_prefixes": True,
                    "dry_run": True,
                    "backup_originals": True,
                    "file_patterns": ["test_*.py", "spec_*.py"],
                    "recurse_directories": True,
                    "degradation_tier": "advanced",
                    "format_output": True,
                    "remove_unused_imports": True,
                },
                use_case=ConfigurationProfile.CUSTOM_TESTING_FRAMEWORK,
            ),
            "enterprise_deployment": ConfigurationTemplate(
                name="Enterprise Deployment",
                description="Production-ready configuration for enterprise environments",
                config_dict={
                    "target_root": "./converted",
                    "backup_root": "./backups",
                    "backup_originals": True,
                    "fail_fast": True,
                    "continue_on_error": False,
                    "file_patterns": ["test_*.py", "**/test_*.py"],
                    "recurse_directories": True,
                    "max_file_size_mb": 50,
                    "max_concurrent_files": 4,
                    "cache_analysis_results": True,
                    "degradation_tier": "advanced",
                    "format_output": True,
                    "remove_unused_imports": True,
                },
                use_case=ConfigurationProfile.ENTERPRISE_DEPLOYMENT,
            ),
            "ci_integration": ConfigurationTemplate(
                name="CI Integration",
                description="Optimized configuration for continuous integration environments",
                config_dict={
                    "dry_run": False,
                    "fail_fast": True,
                    "max_concurrent_files": 8,
                    "cache_analysis_results": True,
                    "file_patterns": ["test_*.py"],
                    "recurse_directories": True,
                    "max_file_size_mb": 20,
                    "degradation_tier": "advanced",
                    "format_output": True,
                    "remove_unused_imports": True,
                    "line_length": 100,
                },
                use_case=ConfigurationProfile.CI_INTEGRATION,
            ),
            "development_debugging": ConfigurationTemplate(
                name="Development Debugging",
                description="Configuration optimized for development and debugging workflows",
                config_dict={
                    "dry_run": True,
                    "create_source_map": True,
                    "log_level": "DEBUG",
                    "max_file_size_mb": 5,
                    "file_patterns": ["test_*.py"],
                    "recurse_directories": False,
                    "degradation_tier": "experimental",
                    "format_output": True,
                    "remove_unused_imports": False,
                },
                use_case=ConfigurationProfile.DEVELOPMENT_DEBUGGING,
            ),
            "production_deployment": ConfigurationTemplate(
                name="Production Deployment",
                description="Conservative configuration for production deployments",
                config_dict={
                    "dry_run": False,
                    "backup_originals": True,
                    "target_root": "./converted",
                    "backup_root": "./backups",
                    "fail_fast": True,
                    "continue_on_error": False,
                    "file_patterns": ["test_*.py"],
                    "recurse_directories": True,
                    "max_file_size_mb": 30,
                    "degradation_tier": "essential",
                    "format_output": True,
                    "remove_unused_imports": True,
                    "line_length": 100,
                },
                use_case=ConfigurationProfile.PRODUCTION_DEPLOYMENT,
            ),
        }

    def get_template(self, name: str) -> ConfigurationTemplate | None:
        """Get a specific template by name."""
        return self.templates.get(name)

    def get_templates_by_use_case(self, use_case: str) -> list[ConfigurationTemplate]:
        """Get all templates for a specific use case."""
        return [template for template in self.templates.values() if template.use_case == use_case]

    def get_all_templates(self) -> dict[str, ConfigurationTemplate]:
        """Get all available templates."""
        return self.templates.copy()

    def get_template_names(self) -> list[str]:
        """Get list of all template names."""
        return list(self.templates.keys())

    def suggest_template_for_config(self, config: ValidatedMigrationConfig) -> ConfigurationTemplate | None:
        """Suggest the best template for a given configuration."""
        detector = ConfigurationUseCaseDetector()
        use_case = detector.detect_use_case(config)

        templates = self.get_templates_by_use_case(use_case)
        if templates:
            return templates[0]  # Return first template for the detected use case

        return None


# Global template manager instance
_template_manager = ConfigurationTemplateManager()


def get_configuration_template_manager() -> ConfigurationTemplateManager:
    """Get the global configuration template manager."""
    return _template_manager


def get_template(name: str) -> ConfigurationTemplate | None:
    """Convenience function to get a specific template."""
    return _template_manager.get_template(name)


def list_available_templates() -> list[str]:
    """Get list of all available template names."""
    return _template_manager.get_template_names()


def generate_config_from_template(template_name: str) -> dict:
    """Generate configuration dictionary from a template."""
    template = _template_manager.get_template(template_name)
    if template:
        return template.config_dict.copy()
    raise ValueError(f"Template not found: {template_name}")
