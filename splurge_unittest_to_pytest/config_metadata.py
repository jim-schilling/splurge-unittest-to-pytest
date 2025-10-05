"""Configuration field metadata system for enhanced documentation and validation.

This module provides rich metadata for all configuration fields, enabling
auto-generated documentation, better error messages, and intelligent suggestions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ConfigurationField:
    """Rich metadata for a configuration field."""

    name: str
    type: str
    description: str
    examples: list[str]
    constraints: list[str]
    related_fields: list[str]
    common_mistakes: list[str]
    default_value: Any
    category: str
    importance: str  # 'required', 'recommended', 'optional'
    cli_flag: str | None = None
    environment_variable: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "examples": self.examples,
            "constraints": self.constraints,
            "related_fields": self.related_fields,
            "common_mistakes": self.common_mistakes,
            "default_value": self.default_value,
            "category": self.category,
            "importance": self.importance,
            "cli_flag": self.cli_flag,
            "environment_variable": self.environment_variable,
        }


class ConfigurationMetadataRegistry:
    """Registry of metadata for all configuration fields."""

    def __init__(self):
        self._fields: dict[str, ConfigurationField] = {}
        self._categories: dict[str, list[str]] = {}
        self._initialize_metadata()

    def _initialize_metadata(self):
        """Initialize metadata for all configuration fields."""
        # Output settings
        self._add_field(
            ConfigurationField(
                name="target_root",
                type="str | None",
                description="Root directory where transformed files will be written. If None, files are written alongside originals with a suffix.",
                examples=["./output", "/tmp/migrated", "migrated_tests"],
                constraints=["Must be a writable directory if specified", "Cannot be used with dry_run=True"],
                related_fields=["dry_run", "target_suffix", "target_extension"],
                common_mistakes=[
                    "Using a relative path that doesn't exist",
                    "Forgetting to create the directory first",
                    "Using the same directory as source files without a suffix",
                ],
                default_value=None,
                category="Output Settings",
                importance="recommended",
                cli_flag="--target-root",
                environment_variable="SPLURGE_TARGET_ROOT",
            )
        )

        self._add_field(
            ConfigurationField(
                name="root_directory",
                type="str | None",
                description="Root directory to scan for test files. If None, uses current working directory.",
                examples=["./tests", "src/tests", "/path/to/project/tests"],
                constraints=["Must be a readable directory if specified"],
                related_fields=["file_patterns", "recurse_directories"],
                common_mistakes=[
                    "Using a path that doesn't exist",
                    "Forgetting this is the scan root, not just a subdirectory",
                ],
                default_value=None,
                category="Output Settings",
                importance="optional",
                cli_flag="--root-directory",
                environment_variable="SPLURGE_ROOT_DIRECTORY",
            )
        )

        self._add_field(
            ConfigurationField(
                name="file_patterns",
                type="list[str]",
                description="Glob patterns to match test files for transformation.",
                examples=["test_*.py", ["test_*.py", "spec_*.py"], "**/test_*.py"],
                constraints=["At least one pattern required", "Must be valid glob patterns"],
                related_fields=["root_directory", "recurse_directories"],
                common_mistakes=[
                    "Using regex instead of glob patterns",
                    "Forgetting wildcards (*, **, ?)",
                    "Not including .py extension",
                ],
                default_value=["test_*.py"],
                category="Output Settings",
                importance="required",
                cli_flag="--file-patterns",
                environment_variable="SPLURGE_FILE_PATTERNS",
            )
        )

        self._add_field(
            ConfigurationField(
                name="recurse_directories",
                type="bool",
                description="Whether to recursively scan subdirectories for test files.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["root_directory", "file_patterns"],
                common_mistakes=[
                    "Setting to false when you have nested test directories",
                    "Not understanding this affects the entire directory tree",
                ],
                default_value=True,
                category="Output Settings",
                importance="recommended",
                cli_flag="--recurse-directories",
                environment_variable="SPLURGE_RECURSE_DIRECTORIES",
            )
        )

        self._add_field(
            ConfigurationField(
                name="backup_originals",
                type="bool",
                description="Whether to create backup copies of original files before transformation.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["backup_root"],
                common_mistakes=[
                    "Disabling backups thinking they're not needed",
                    "Not having enough disk space for backups",
                ],
                default_value=True,
                category="Output Settings",
                importance="recommended",
                cli_flag="--backup-originals",
                environment_variable="SPLURGE_BACKUP_ORIGINALS",
            )
        )

        self._add_field(
            ConfigurationField(
                name="backup_root",
                type="str | None",
                description="Directory where backup files will be stored. If None, backups are stored alongside originals.",
                examples=["./backups", "/tmp/backups", "original_tests"],
                constraints=["Must be writable if specified", "Cannot be used when backup_originals=False"],
                related_fields=["backup_originals"],
                common_mistakes=[
                    "Using the same directory as target_root",
                    "Not having write permissions to the backup directory",
                ],
                default_value=None,
                category="Output Settings",
                importance="optional",
                cli_flag="--backup-root",
                environment_variable="SPLURGE_BACKUP_ROOT",
            )
        )

        self._add_field(
            ConfigurationField(
                name="target_suffix",
                type="str",
                description="Suffix to append to transformed filenames (used when target_root is None).",
                examples=["_pytest", "_migrated", ".new"],
                constraints=[],
                related_fields=["target_root", "target_extension"],
                common_mistakes=[
                    "Using characters that aren't valid in filenames",
                    "Not understanding this creates new files alongside originals",
                ],
                default_value="",
                category="Output Settings",
                importance="optional",
                cli_flag="--target-suffix",
                environment_variable="SPLURGE_TARGET_SUFFIX",
            )
        )

        self._add_field(
            ConfigurationField(
                name="target_extension",
                type="str | None",
                description="File extension for transformed files. If None, uses original extension.",
                examples=[".py", ".pytest.py"],
                constraints=["Must be a valid file extension if specified"],
                related_fields=["target_suffix"],
                common_mistakes=[
                    "Including the dot in the extension",
                    "Using an extension that conflicts with the target language",
                ],
                default_value=None,
                category="Output Settings",
                importance="optional",
                cli_flag="--target-extension",
                environment_variable="SPLURGE_TARGET_EXTENSION",
            )
        )

        # Transformation settings
        self._add_field(
            ConfigurationField(
                name="line_length",
                type="int | None",
                description="Maximum line length for formatted output code.",
                examples=["120", "100", "80"],
                constraints=["Must be between 60-200 if specified"],
                related_fields=["format_output"],
                common_mistakes=[
                    "Setting too low causing excessive line breaks",
                    "Not understanding this only affects formatted output",
                ],
                default_value=120,
                category="Transformation Settings",
                importance="optional",
                cli_flag="--line-length",
                environment_variable="SPLURGE_LINE_LENGTH",
            )
        )

        self._add_field(
            ConfigurationField(
                name="assert_almost_equal_places",
                type="int",
                description="Default decimal places for assertAlmostEqual transformations.",
                examples=["7", "3", "10"],
                constraints=["Must be between 1-15"],
                related_fields=[],
                common_mistakes=[
                    "Using too few places for floating point comparisons",
                    "Not understanding this affects precision of generated tests",
                ],
                default_value=7,
                category="Transformation Settings",
                importance="optional",
                cli_flag="--assert-almost-equal-places",
                environment_variable="SPLURGE_ASSERT_ALMOST_EQUAL_PLACES",
            )
        )

        self._add_field(
            ConfigurationField(
                name="log_level",
                type="str",
                description="Logging verbosity level for transformation process.",
                examples=["INFO", "DEBUG", "WARNING"],
                constraints=["Must be one of: DEBUG, INFO, WARNING, ERROR"],
                related_fields=[],
                common_mistakes=[
                    "Using DEBUG in production causing log spam",
                    "Not increasing verbosity when troubleshooting issues",
                ],
                default_value="INFO",
                category="Transformation Settings",
                importance="optional",
                cli_flag="--log-level",
                environment_variable="SPLURGE_LOG_LEVEL",
            )
        )

        self._add_field(
            ConfigurationField(
                name="max_file_size_mb",
                type="int",
                description="Maximum file size to process in megabytes.",
                examples=["10", "50", "5"],
                constraints=["Must be between 1-100"],
                related_fields=[],
                common_mistakes=["Setting too low for large test files", "Setting too high causing memory issues"],
                default_value=10,
                category="Transformation Settings",
                importance="optional",
                cli_flag="--max-file-size-mb",
                environment_variable="SPLURGE_MAX_FILE_SIZE_MB",
            )
        )

        self._add_field(
            ConfigurationField(
                name="dry_run",
                type="bool",
                description="Perform a dry run without writing any files.",
                examples=["true", "false"],
                constraints=["Cannot be used with target_root"],
                related_fields=["target_root"],
                common_mistakes=[
                    "Thinking dry run still creates output files",
                    "Not using dry run when testing new configurations",
                ],
                default_value=False,
                category="Transformation Settings",
                importance="recommended",
                cli_flag="--dry-run",
                environment_variable="SPLURGE_DRY_RUN",
            )
        )

        self._add_field(
            ConfigurationField(
                name="fail_fast",
                type="bool",
                description="Stop processing on the first error encountered.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["continue_on_error"],
                common_mistakes=[
                    "Using in CI when you want to see all errors",
                    "Not using when debugging a single failing file",
                ],
                default_value=False,
                category="Transformation Settings",
                importance="optional",
                cli_flag="--fail-fast",
                environment_variable="SPLURGE_FAIL_FAST",
            )
        )

        # Continue with remaining fields...
        self._add_field(
            ConfigurationField(
                name="format_output",
                type="bool",
                description="Whether to format output code with black and isort.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["line_length"],
                common_mistakes=[
                    "Disabling when you want consistent code formatting",
                    "Not having black/isort installed when enabled",
                ],
                default_value=True,
                category="Import Handling",
                importance="recommended",
                cli_flag="--format-output",
                environment_variable="SPLURGE_FORMAT_OUTPUT",
            )
        )

        self._add_field(
            ConfigurationField(
                name="remove_unused_imports",
                type="bool",
                description="Whether to remove unused unittest imports after transformation.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["transform_imports"],
                common_mistakes=[
                    "Disabling when you want clean imports",
                    "Not understanding this only affects unittest imports",
                ],
                default_value=True,
                category="Import Handling",
                importance="recommended",
                cli_flag="--remove-unused-imports",
                environment_variable="SPLURGE_REMOVE_UNUSED_IMPORTS",
            )
        )

        self._add_field(
            ConfigurationField(
                name="preserve_import_comments",
                type="bool",
                description="Whether to preserve comments in import sections.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["transform_imports"],
                common_mistakes=[
                    "Disabling when you have important import comments",
                    "Not understanding this preserves comment positioning",
                ],
                default_value=True,
                category="Import Handling",
                importance="optional",
                cli_flag="--preserve-import-comments",
                environment_variable="SPLURGE_PRESERVE_IMPORT_COMMENTS",
            )
        )

        # Transform selection options
        self._add_field(
            ConfigurationField(
                name="transform_assertions",
                type="bool",
                description="Whether to transform unittest assertions to pytest equivalents.",
                examples=["true", "false"],
                constraints=[],
                related_fields=[],
                common_mistakes=[
                    "Disabling when you want full unittest to pytest conversion",
                    "Not understanding this is the core transformation",
                ],
                default_value=True,
                category="Transform Selection",
                importance="required",
                cli_flag="--transform-assertions",
                environment_variable="SPLURGE_TRANSFORM_ASSERTIONS",
            )
        )

        self._add_field(
            ConfigurationField(
                name="transform_setup_teardown",
                type="bool",
                description="Whether to convert setUp/tearDown methods to pytest fixtures.",
                examples=["true", "false"],
                constraints=[],
                related_fields=[],
                common_mistakes=[
                    "Disabling when you have setUp/tearDown methods",
                    "Not understanding the fixture conversion process",
                ],
                default_value=True,
                category="Transform Selection",
                importance="recommended",
                cli_flag="--transform-setup-teardown",
                environment_variable="SPLURGE_TRANSFORM_SETUP_TEARDOWN",
            )
        )

        self._add_field(
            ConfigurationField(
                name="transform_subtests",
                type="bool",
                description="Whether to attempt subTest conversions to pytest parametrize.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["parametrize"],
                common_mistakes=[
                    "Disabling when you have subTest usage",
                    "Not understanding subTest complexity can cause failures",
                ],
                default_value=True,
                category="Transform Selection",
                importance="optional",
                cli_flag="--transform-subtests",
                environment_variable="SPLURGE_TRANSFORM_SUBTESTS",
            )
        )

        self._add_field(
            ConfigurationField(
                name="transform_skip_decorators",
                type="bool",
                description="Whether to convert unittest skip decorators to pytest equivalents.",
                examples=["true", "false"],
                constraints=[],
                related_fields=[],
                common_mistakes=[
                    "Disabling when you have skip decorators",
                    "Not understanding pytest skip syntax differences",
                ],
                default_value=True,
                category="Transform Selection",
                importance="recommended",
                cli_flag="--transform-skip-decorators",
                environment_variable="SPLURGE_TRANSFORM_SKIP_DECORATORS",
            )
        )

        self._add_field(
            ConfigurationField(
                name="transform_imports",
                type="bool",
                description="Whether to transform unittest imports to pytest equivalents.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["remove_unused_imports"],
                common_mistakes=[
                    "Disabling when you want full import conversion",
                    "Not understanding this affects import statements",
                ],
                default_value=True,
                category="Transform Selection",
                importance="required",
                cli_flag="--transform-imports",
                environment_variable="SPLURGE_TRANSFORM_IMPORTS",
            )
        )

        # Processing options
        self._add_field(
            ConfigurationField(
                name="continue_on_error",
                type="bool",
                description="Whether to continue processing other files when one file fails.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["fail_fast"],
                common_mistakes=[
                    "Disabling in development when you want to see all errors",
                    "Enabling in CI when you want fast failure feedback",
                ],
                default_value=False,
                category="Processing Options",
                importance="optional",
                cli_flag="--continue-on-error",
                environment_variable="SPLURGE_CONTINUE_ON_ERROR",
            )
        )

        self._add_field(
            ConfigurationField(
                name="max_concurrent_files",
                type="int",
                description="Maximum number of files to process concurrently.",
                examples=["1", "4", "8"],
                constraints=["Must be between 1-50"],
                related_fields=[],
                common_mistakes=[
                    "Setting too high causing resource exhaustion",
                    "Setting to 1 when you have many files to process",
                ],
                default_value=1,
                category="Processing Options",
                importance="optional",
                cli_flag="--max-concurrent-files",
                environment_variable="SPLURGE_MAX_CONCURRENT_FILES",
            )
        )

        self._add_field(
            ConfigurationField(
                name="cache_analysis_results",
                type="bool",
                description="Whether to cache analysis results for improved performance.",
                examples=["true", "false"],
                constraints=[],
                related_fields=[],
                common_mistakes=[
                    "Disabling when you have repeated runs on same files",
                    "Not understanding this improves performance for large codebases",
                ],
                default_value=True,
                category="Processing Options",
                importance="optional",
                cli_flag="--cache-analysis-results",
                environment_variable="SPLURGE_CACHE_ANALYSIS_RESULTS",
            )
        )

        # Advanced options
        self._add_field(
            ConfigurationField(
                name="preserve_file_encoding",
                type="bool",
                description="Whether to preserve original file encoding in output files.",
                examples=["true", "false"],
                constraints=[],
                related_fields=[],
                common_mistakes=[
                    "Disabling when you have non-UTF-8 files",
                    "Not understanding encoding preservation implications",
                ],
                default_value=True,
                category="Advanced Options",
                importance="optional",
                cli_flag="--preserve-file-encoding",
                environment_variable="SPLURGE_PRESERVE_FILE_ENCODING",
            )
        )

        self._add_field(
            ConfigurationField(
                name="create_source_map",
                type="bool",
                description="Whether to create source mapping for debugging transformations.",
                examples=["true", "false"],
                constraints=[],
                related_fields=[],
                common_mistakes=[
                    "Enabling in production causing unnecessary overhead",
                    "Not enabling when debugging transformation issues",
                ],
                default_value=False,
                category="Advanced Options",
                importance="optional",
                cli_flag="--create-source-map",
                environment_variable="SPLURGE_CREATE_SOURCE_MAP",
            )
        )

        self._add_field(
            ConfigurationField(
                name="max_depth",
                type="int",
                description="Maximum depth to traverse nested control flow structures.",
                examples=["7", "5", "10"],
                constraints=["Must be between 3-15"],
                related_fields=[],
                common_mistakes=[
                    "Setting too low causing incomplete transformations",
                    "Setting too high causing performance issues",
                ],
                default_value=7,
                category="Advanced Options",
                importance="optional",
                cli_flag="--max-depth",
                environment_variable="SPLURGE_MAX_DEPTH",
            )
        )

        # Test method patterns
        self._add_field(
            ConfigurationField(
                name="test_method_prefixes",
                type="list[str]",
                description="Prefixes that identify test methods for transformation.",
                examples=[["test"], ["test", "spec", "should"], ["test", "it", "describe"]],
                constraints=["At least one prefix required"],
                related_fields=[],
                common_mistakes=[
                    "Not including all your test method prefixes",
                    "Using prefixes that conflict with non-test methods",
                ],
                default_value=["test", "spec", "should", "it"],
                category="Test Method Patterns",
                importance="required",
                cli_flag="--test-method-prefixes",
                environment_variable="SPLURGE_TEST_METHOD_PREFIXES",
            )
        )

        # Parametrize settings
        self._add_field(
            ConfigurationField(
                name="parametrize",
                type="bool",
                description="Whether to convert unittest subTests to pytest parametrize.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["transform_subtests", "parametrize_ids", "parametrize_type_hints"],
                common_mistakes=[
                    "Disabling when you want subTest conversion",
                    "Not understanding parametrize vs subTest differences",
                ],
                default_value=True,
                category="Parametrize Settings",
                importance="optional",
                cli_flag="--parametrize",
                environment_variable="SPLURGE_PARAMETRIZE",
            )
        )

        self._add_field(
            ConfigurationField(
                name="parametrize_ids",
                type="bool",
                description="Whether to add ids parameter to parametrize decorators.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["parametrize"],
                common_mistakes=[
                    "Enabling without understanding id generation",
                    "Not using ids for better test output readability",
                ],
                default_value=False,
                category="Parametrize Settings",
                importance="optional",
                cli_flag="--parametrize-ids",
                environment_variable="SPLURGE_PARAMETRIZE_IDS",
            )
        )

        self._add_field(
            ConfigurationField(
                name="parametrize_type_hints",
                type="bool",
                description="Whether to add type hints to parametrize parameters.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["parametrize"],
                common_mistakes=[
                    "Enabling without having type information available",
                    "Not understanding type hint generation limitations",
                ],
                default_value=False,
                category="Parametrize Settings",
                importance="optional",
                cli_flag="--parametrize-type-hints",
                environment_variable="SPLURGE_PARAMETRIZE_TYPE_HINTS",
            )
        )

        # Degradation settings
        self._add_field(
            ConfigurationField(
                name="degradation_enabled",
                type="bool",
                description="Whether to enable degradation for failed transformations.",
                examples=["true", "false"],
                constraints=[],
                related_fields=["degradation_tier"],
                common_mistakes=[
                    "Disabling when you want robust transformation fallbacks",
                    "Not understanding degradation provides partial results",
                ],
                default_value=True,
                category="Degradation Settings",
                importance="recommended",
                cli_flag="--degradation-enabled",
                environment_variable="SPLURGE_DEGRADATION_ENABLED",
            )
        )

        self._add_field(
            ConfigurationField(
                name="degradation_tier",
                type="str",
                description="Degradation tier determining fallback behavior (essential, advanced, experimental).",
                examples=["essential", "advanced", "experimental"],
                constraints=["Must be one of: essential, advanced, experimental"],
                related_fields=["degradation_enabled", "dry_run"],
                common_mistakes=[
                    "Using experimental without dry_run first",
                    "Not understanding tier differences in transformation quality",
                ],
                default_value="advanced",
                category="Degradation Settings",
                importance="optional",
                cli_flag="--degradation-tier",
                environment_variable="SPLURGE_DEGRADATION_TIER",
            )
        )

    def _add_field(self, field: ConfigurationField):
        """Add a field to the registry."""
        self._fields[field.name] = field
        if field.category not in self._categories:
            self._categories[field.category] = []
        self._categories[field.category].append(field.name)

    def get_field(self, name: str) -> ConfigurationField | None:
        """Get metadata for a specific field."""
        return self._fields.get(name)

    def get_all_fields(self) -> dict[str, ConfigurationField]:
        """Get all field metadata."""
        return self._fields.copy()

    def get_fields_by_category(self, category: str) -> list[ConfigurationField]:
        """Get all fields in a specific category."""
        return [self._fields[name] for name in self._categories.get(category, []) if name in self._fields]

    def get_categories(self) -> list[str]:
        """Get all available categories."""
        return list(self._categories.keys())

    def validate_metadata_completeness(self) -> list[str]:
        """Validate that all fields have complete metadata."""
        missing = []
        for name, field in self._fields.items():
            if not field.description:
                missing.append(f"{name}: missing description")
            if not field.examples:
                missing.append(f"{name}: missing examples")
            if field.importance not in ["required", "recommended", "optional"]:
                missing.append(f"{name}: invalid importance level")
        return missing


# Global registry instance
metadata_registry = ConfigurationMetadataRegistry()


def get_field_metadata(field_name: str) -> ConfigurationField | None:
    """Get metadata for a configuration field."""
    return metadata_registry.get_field(field_name)


def get_all_field_metadata() -> dict[str, ConfigurationField]:
    """Get metadata for all configuration fields."""
    return metadata_registry.get_all_fields()


def get_fields_by_category(category: str) -> list[ConfigurationField]:
    """Get all fields in a specific category."""
    return metadata_registry.get_fields_by_category(category)


def get_categories() -> list[str]:
    """Get all available categories."""
    return metadata_registry.get_categories()


__all__ = [
    "ConfigurationField",
    "ConfigurationMetadataRegistry",
    "get_field_metadata",
    "get_all_field_metadata",
    "get_fields_by_category",
    "get_categories",
    "metadata_registry",
]
