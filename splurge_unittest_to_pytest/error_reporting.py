"""Advanced error reporting system for intelligent error handling and recovery.

This module provides sophisticated error classification, context-aware suggestions,
and interactive recovery workflows to help users resolve configuration and migration
issues more effectively.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from .exceptions import MigrationError

if TYPE_CHECKING:
    pass


class ErrorCategory(Enum):
    """Categorized error types for better handling and suggestions."""

    CONFIGURATION = "configuration"
    FILESYSTEM = "filesystem"
    PARSING = "parsing"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    PERMISSION = "permission"
    DEPENDENCY = "dependency"
    NETWORK = "network"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels for prioritization and user experience."""

    CRITICAL = "critical"  # Blocks operation completely, requires immediate attention
    HIGH = "high"  # Major issues requiring prompt attention
    MEDIUM = "medium"  # Issues that affect results but operation can continue
    LOW = "low"  # Minor issues or warnings that don't affect operation
    INFO = "info"  # Informational messages for user awareness


@dataclass
class Suggestion:
    """A structured suggestion for error resolution."""

    message: str
    action: str
    examples: list[str] | None = None
    priority: int = 1  # Lower numbers = higher priority
    category: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert suggestion to dictionary for serialization."""
        return {
            "message": self.message,
            "action": self.action,
            "examples": self.examples or [],
            "priority": self.priority,
            "category": self.category,
        }


class SmartError(MigrationError):
    """Enhanced error with rich context, classification, and recovery suggestions.

    This class extends MigrationError to provide structured error information
    including categorization, severity assessment, and intelligent suggestions
    for resolution.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict[str, Any] | None = None,
        suggestions: list[Suggestion] | None = None,
        recovery_actions: list[str] | None = None,
        source_exception: Exception | None = None,
    ):
        """Initialize SmartError with enhanced context.

        Args:
            message: Human-readable error message
            category: Error classification for targeted handling
            severity: Severity level for prioritization
            context: Additional context data (file paths, line numbers, etc.)
            suggestions: List of suggested resolution steps
            recovery_actions: List of specific recovery actions to take
            source_exception: Original exception that triggered this error
        """
        super().__init__(
            message,
            {
                "category": category.value,
                "severity": severity.value,
                "context": context or {},
                "suggestions": [s.to_dict() for s in suggestions or []],
                "recovery_actions": recovery_actions or [],
                "source_exception": str(source_exception) if source_exception else None,
            },
        )

        self.category = category
        self.severity = severity
        self.context = context or {}
        self.suggestions = suggestions or []
        self.recovery_actions = recovery_actions or []
        self.source_exception = source_exception

    def add_suggestion(self, suggestion: Suggestion) -> Self:
        """Add a suggestion to this error."""
        self.suggestions.append(suggestion)
        self.details["suggestions"] = [s.to_dict() for s in self.suggestions]
        return self

    def get_prioritized_suggestions(self) -> list[Suggestion]:
        """Get suggestions sorted by priority (lowest number first)."""
        return sorted(self.suggestions, key=lambda s: s.priority)

    def is_recoverable(self) -> bool:
        """Check if this error type is generally recoverable."""
        return self.category in {
            ErrorCategory.CONFIGURATION,
            ErrorCategory.FILESYSTEM,
            ErrorCategory.PERMISSION,
            ErrorCategory.DEPENDENCY,
        }

    def to_user_friendly_message(self) -> str:
        """Generate a user-friendly error message with suggestions."""
        message = f"[{self.severity.value.upper()}] {self.message}"

        if self.suggestions:
            message += "\n\nSuggestions:"
            for i, suggestion in enumerate(self.get_prioritized_suggestions()[:3], 1):
                message += f"\n  {i}. {suggestion.message}"
                if suggestion.action:
                    message += f" - {suggestion.action}"
                if suggestion.examples:
                    message += f" (e.g., {suggestion.examples[0]})"

        if self.recovery_actions:
            message += "\n\nNext steps:"
            for action in self.recovery_actions[:2]:
                message += f"\n  • {action}"

        return message


class ErrorSeverityAssessor:
    """Assesses error severity based on context and impact."""

    def __init__(self):
        self.severity_rules = {
            "category_defaults": {
                "transformation": ErrorSeverity.CRITICAL,
                "parsing": ErrorSeverity.CRITICAL,
                "validation": ErrorSeverity.HIGH,
                "configuration": ErrorSeverity.HIGH,
                "filesystem": ErrorSeverity.HIGH,
                "permission": ErrorSeverity.HIGH,
                "dependency": ErrorSeverity.MEDIUM,
                "network": ErrorSeverity.LOW,
                "resource": ErrorSeverity.MEDIUM,
            },
            "context_indicators": {
                "file_not_found": ErrorSeverity.HIGH,
                "permission_denied": ErrorSeverity.HIGH,
                "invalid_syntax": ErrorSeverity.CRITICAL,
                "missing_dependency": ErrorSeverity.MEDIUM,
                "network_timeout": ErrorSeverity.LOW,
                "disk_full": ErrorSeverity.HIGH,
            },
        }

    def assess_severity(self, error: Exception, context: dict[str, Any] | None = None) -> ErrorSeverity:
        """Assess the severity of an error based on type and context."""
        context = context or {}

        # Check for context indicators first
        for indicator, severity in self.severity_rules["context_indicators"].items():
            if indicator in str(error).lower() or indicator in context:
                return severity

        # Fall back to category-based assessment
        if isinstance(error, SmartError):
            category = error.category
        else:
            # Map common exception types to categories
            category = self._infer_category_from_exception(error)

        return self.severity_rules["category_defaults"].get(category.value, ErrorSeverity.MEDIUM)

    def _infer_category_from_exception(self, error: Exception) -> ErrorCategory:
        """Infer error category from exception type and message."""
        error_str = str(error).lower()
        message = error.__class__.__name__.lower()

        if any(term in message + error_str for term in ["permission", "access", "forbidden"]):
            return ErrorCategory.PERMISSION
        elif any(
            term in message + error_str
            for term in ["file", "path", "directory", "target_root", "does not exist", "nonexistent", "missing"]
        ):
            return ErrorCategory.FILESYSTEM
        elif any(term in message + error_str for term in ["parse", "syntax", "invalid"]):
            return ErrorCategory.PARSING
        elif any(term in message + error_str for term in ["transform", "convert"]):
            return ErrorCategory.TRANSFORMATION
        elif any(term in message + error_str for term in ["config", "parameter", "option"]):
            return ErrorCategory.CONFIGURATION
        elif any(term in message + error_str for term in ["import", "module", "package"]):
            return ErrorCategory.DEPENDENCY

        return ErrorCategory.UNKNOWN


class ErrorSuggestionEngine:
    """Generates intelligent suggestions based on error context and patterns."""

    def __init__(self):
        self.suggestion_patterns = self._build_suggestion_patterns()

    def generate_suggestions(self, error: SmartError) -> list[Suggestion]:
        """Generate context-aware suggestions for error resolution."""
        suggestions = []

        # Category-specific suggestions
        category_suggestions = self._generate_category_suggestions(error)
        suggestions.extend(category_suggestions)

        # Context-specific suggestions
        context_suggestions = self._generate_context_suggestions(error)
        suggestions.extend(context_suggestions)

        # Pattern-based suggestions
        pattern_suggestions = self._generate_pattern_suggestions(error)
        suggestions.extend(pattern_suggestions)

        # Remove duplicates and prioritize
        seen = set()
        unique_suggestions = []
        for suggestion in sorted(suggestions, key=lambda s: s.priority):
            key = (suggestion.message, suggestion.action)
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)

        return unique_suggestions

    def _generate_category_suggestions(self, error: SmartError) -> list[Suggestion]:
        """Generate suggestions based on error category."""
        suggestions = []

        if error.category == ErrorCategory.CONFIGURATION:
            suggestions.extend(self._generate_config_suggestions(error))
        elif error.category == ErrorCategory.FILESYSTEM:
            suggestions.extend(self._generate_filesystem_suggestions(error))
        elif error.category == ErrorCategory.PERMISSION:
            suggestions.extend(self._generate_permission_suggestions(error))
        elif error.category == ErrorCategory.DEPENDENCY:
            suggestions.extend(self._generate_dependency_suggestions(error))
        elif error.category == ErrorCategory.TRANSFORMATION:
            suggestions.extend(self._generate_transformation_suggestions(error))

        return suggestions

    def _generate_config_suggestions(self, error: SmartError) -> list[Suggestion]:
        """Generate configuration-specific suggestions."""
        suggestions = []

        error_msg = str(error).lower()

        if "invalid file pattern" in error_msg or "test_[" in error_msg or "pattern" in error_msg:
            suggestions.append(
                Suggestion(
                    message="File pattern contains invalid syntax",
                    action="Use glob patterns like 'test_*.py' or '*.py'",
                    examples=["test_*.py", "**/test_*.py", "tests/**/*.py"],
                    priority=1,
                    category="correction",
                )
            )

        if "target_root" in error.context and not error.context.get("target_root_exists"):
            suggestions.append(
                Suggestion(
                    message="Target directory does not exist",
                    action="Create target directory or use existing path",
                    examples=[error.context.get("target_root", "./output"), "./output", "/tmp/migration"],
                    priority=1,
                    category="action",
                )
            )

        if "backup_root" in error.context and not error.context.get("backup_root_exists"):
            suggestions.append(
                Suggestion(
                    message="Backup directory does not exist",
                    action="Create backup directory or use existing path",
                    examples=[error.context.get("backup_root", "./backups"), "./backups", "/tmp/backups"],
                    priority=2,
                    category="action",
                )
            )

        if "dry_run" in error_msg and "target_root" in error_msg:
            suggestions.append(
                Suggestion(
                    message="dry_run mode ignores target_root setting",
                    action="Remove target_root parameter or set dry_run=False",
                    examples=["--dry-run", "--target-root ./output"],
                    priority=1,
                    category="correction",
                )
            )

        return suggestions

    def _generate_filesystem_suggestions(self, error: SmartError) -> list[Suggestion]:
        """Generate filesystem-specific suggestions."""
        suggestions = []

        if (
            "no such file or directory" in str(error).lower()
            or "file not found" in str(error).lower()
            or "does not exist" in str(error).lower()
            or "target_root" in str(error).lower()
        ):
            suggestions.append(
                Suggestion(
                    message="Specified file or directory does not exist",
                    action="Check file path and ensure it exists",
                    examples=["./tests/", "/path/to/tests/"],
                    priority=1,
                    category="action",
                )
            )

        if "permission denied" in str(error).lower():
            suggestions.append(
                Suggestion(
                    message="Insufficient permissions for file operation",
                    action="Check file permissions or run with appropriate privileges",
                    examples=["chmod +r file.py", "sudo python script.py"],
                    priority=1,
                    category="permission",
                )
            )

        return suggestions

    def _generate_permission_suggestions(self, error: SmartError) -> list[Suggestion]:
        """Generate permission-specific suggestions."""
        suggestions = []

        suggestions.append(
            Suggestion(
                message="Permission denied for file operation",
                action="Check file permissions and user privileges",
                examples=["chmod +rwx file.py", "sudo python script.py", "chown user file.py"],
                priority=1,
                category="permission",
            )
        )

        return suggestions

    def _generate_dependency_suggestions(self, error: SmartError) -> list[Suggestion]:
        """Generate dependency-specific suggestions."""
        suggestions = []

        if "no module named" in str(error).lower():
            suggestions.append(
                Suggestion(
                    message="Required module is not installed",
                    action="Install the missing dependency",
                    examples=["pip install missing-package", "conda install missing-package"],
                    priority=1,
                    category="dependency",
                )
            )

        return suggestions

    def _generate_transformation_suggestions(self, error: SmartError) -> list[Suggestion]:
        """Generate transformation-specific suggestions."""
        suggestions = []

        if "cannot convert" in str(error).lower():
            suggestions.append(
                Suggestion(
                    message="Code pattern cannot be automatically converted",
                    action="Manual intervention required for this specific pattern",
                    examples=["Review the specific code section", "Consider alternative transformation"],
                    priority=2,
                    category="manual",
                )
            )

        return suggestions

    def _generate_context_suggestions(self, error: SmartError) -> list[Suggestion]:
        """Generate suggestions based on error context."""
        suggestions = []

        # Check for specific context clues
        if "line" in error.context and "column" in error.context:
            suggestions.append(
                Suggestion(
                    message=f"Error occurred at line {error.context['line']}, column {error.context['column']} in source file",
                    action=f"Review the code around line {error.context['line']}, column {error.context['column']}",
                    examples=[f"Line {error.context['line']}, Column {error.context['column']}"],
                    priority=3,
                    category="context",
                )
            )

        return suggestions

    def _generate_pattern_suggestions(self, error: SmartError) -> list[Suggestion]:
        """Generate suggestions based on recognized error patterns."""
        suggestions = []

        # Pattern matching for common error scenarios
        error_text = str(error).lower()

        # Common patterns
        if "test_" in error_text and "method" in error_text:
            suggestions.append(
                Suggestion(
                    message="Issue with test method naming or structure",
                    action="Ensure test methods follow pytest naming conventions",
                    examples=["def test_example():", "def test_user_creation():"],
                    priority=2,
                    category="naming",
                )
            )

        return suggestions

    def _build_suggestion_patterns(self) -> dict[str, list[Suggestion]]:
        """Build comprehensive suggestion pattern database."""
        return {
            "file_pattern_errors": [
                Suggestion(
                    message="File pattern syntax error",
                    action="Use valid glob patterns",
                    examples=["test_*.py", "**/test_*.py", "*.py"],
                    priority=1,
                    category="syntax",
                )
            ],
            "permission_errors": [
                Suggestion(
                    message="File permission error",
                    action="Check and fix file permissions",
                    examples=["chmod +r file.py", "sudo python script.py"],
                    priority=1,
                    category="permission",
                )
            ],
            "import_errors": [
                Suggestion(
                    message="Module import failed",
                    action="Install missing dependencies or fix import paths",
                    examples=["pip install package", "PYTHONPATH=/path python script.py"],
                    priority=1,
                    category="dependency",
                )
            ],
        }


@dataclass
class RecoveryStep:
    """A single step in an error recovery workflow."""

    description: str
    action: str
    examples: list[str] | None = None
    validation: str | None = None  # How to validate this step

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "description": self.description,
            "action": self.action,
            "examples": self.examples or [],
            "validation": self.validation,
        }


@dataclass
class RecoveryWorkflow:
    """A complete recovery workflow for an error scenario."""

    title: str
    description: str | None = None
    steps: list[RecoveryStep] | None = None
    estimated_time: str | None = None  # e.g., "5 minutes"
    success_rate: float | None = None  # 0.0 to 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps or []],
            "estimated_time": self.estimated_time,
            "success_rate": self.success_rate,
        }


class ErrorRecoveryAssistant:
    """Provides interactive recovery suggestions and workflows."""

    def __init__(self):
        self.recovery_workflows = self._build_recovery_workflows()

    def suggest_recovery_workflow(self, error: SmartError) -> RecoveryWorkflow | None:
        """Suggest the most appropriate recovery workflow for an error."""
        # Match error to appropriate workflow
        for workflow_name, workflow in self.recovery_workflows.items():
            if self._matches_workflow(error, workflow_name):
                return workflow

        return None

    def _matches_workflow(self, error: SmartError, workflow_name: str) -> bool:
        """Check if error matches a specific workflow pattern."""
        if workflow_name == "configuration_error" and error.category == ErrorCategory.CONFIGURATION:
            return True
        elif workflow_name == "filesystem_error" and error.category == ErrorCategory.FILESYSTEM:
            return True
        elif workflow_name == "permission_error" and error.category == ErrorCategory.PERMISSION:
            return True
        elif workflow_name == "transformation_error" and error.category == ErrorCategory.TRANSFORMATION:
            return True

        return False

    def _build_recovery_workflows(self) -> dict[str, RecoveryWorkflow]:
        """Build comprehensive recovery workflow database."""
        return {
            "configuration_error": RecoveryWorkflow(
                title="Configuration Issue Recovery",
                description="Step-by-step recovery for configuration-related errors",
                steps=[
                    RecoveryStep(
                        description="Review configuration validation errors",
                        action="Check error details for specific field issues and suggestions",
                        validation="Error message contains specific field names",
                    ),
                    RecoveryStep(
                        description="Update configuration file or command line options",
                        action="Apply suggested corrections from error suggestions",
                        examples=["--target-root ./output", "--dry-run"],
                    ),
                    RecoveryStep(
                        description="Re-run migration with corrected configuration",
                        action="Test the migration with --dry-run first to validate changes",
                    ),
                    RecoveryStep(
                        description="Verify the configuration works correctly",
                        action="Check that the migration completes without errors",
                        validation="Migration runs to completion",
                    ),
                ],
                estimated_time="5-10 minutes",
                success_rate=0.9,
            ),
            "filesystem_error": RecoveryWorkflow(
                title="File System Issue Recovery",
                description="Recovery workflow for file and directory related errors",
                steps=[
                    RecoveryStep(
                        description="Identify the problematic file or directory",
                        action="Check error context for specific file paths mentioned",
                        validation="File path is clearly identified in error",
                    ),
                    RecoveryStep(
                        description="Verify file/directory existence and accessibility",
                        action="Check if file exists and has correct permissions",
                        examples=["ls -la file.py", "test -r file.py"],
                    ),
                    RecoveryStep(
                        description="Fix file system issues",
                        action="Create missing directories or fix permissions as needed",
                        examples=["mkdir -p ./output", "chmod +rwx file.py"],
                    ),
                    RecoveryStep(
                        description="Re-run operation after fixes",
                        action="Retry the migration with corrected file paths",
                    ),
                ],
                estimated_time="3-5 minutes",
                success_rate=0.95,
            ),
            "permission_error": RecoveryWorkflow(
                title="Permission Issue Recovery",
                description="Recovery workflow for permission and access related errors",
                steps=[
                    RecoveryStep(
                        description="Identify files requiring permission fixes",
                        action="Check error context for specific file paths with permission issues",
                        validation="File path is identified in error message",
                    ),
                    RecoveryStep(
                        description="Check current file permissions",
                        action="Examine current permissions on problematic files",
                        examples=["ls -la file.py", "stat file.py"],
                    ),
                    RecoveryStep(
                        description="Fix permission issues",
                        action="Change file permissions or run with elevated privileges",
                        examples=["chmod +rwx file.py", "sudo python script.py"],
                    ),
                    RecoveryStep(
                        description="Verify permissions are fixed",
                        action="Confirm files are now accessible",
                        validation="File operations succeed without permission errors",
                    ),
                    RecoveryStep(
                        description="Re-run migration with fixed permissions", action="Retry the migration operation"
                    ),
                ],
                estimated_time="2-5 minutes",
                success_rate=0.98,
            ),
            "transformation_error": RecoveryWorkflow(
                title="Transformation Issue Recovery",
                description="Recovery workflow for code transformation errors",
                steps=[
                    RecoveryStep(
                        description="Identify the problematic code section",
                        action="Check error context for file, line, and column information",
                        validation="Specific location is identified in error",
                    ),
                    RecoveryStep(
                        description="Review the source code around the error location",
                        action="Examine the code that cannot be transformed",
                        examples=["Check line X in file.py for unsupported patterns"],
                    ),
                    RecoveryStep(
                        description="Apply manual fixes if needed",
                        action="Modify the source code to use supported patterns",
                        examples=["Convert subTest to parametrize", "Fix test method naming"],
                    ),
                    RecoveryStep(
                        description="Re-run migration after fixes",
                        action="Test the migration with the corrected source code",
                    ),
                ],
                estimated_time="10-15 minutes",
                success_rate=0.7,
            ),
        }


class ErrorReporter:
    """Central error reporting system that coordinates all error handling components."""

    def __init__(self):
        self.severity_assessor = ErrorSeverityAssessor()
        self.suggestion_engine = ErrorSuggestionEngine()
        self.recovery_assistant = ErrorRecoveryAssistant()

    def enhance_error(self, error: Exception, context: dict[str, Any] | None = None) -> SmartError:
        """Enhance a basic exception with smart error capabilities."""
        if isinstance(error, SmartError):
            return error

        # Assess severity
        severity = self.severity_assessor.assess_severity(error, context)

        # Infer category if not a SmartError
        if isinstance(error, MigrationError):
            # Map existing error types to categories
            category = self._map_migration_error_to_category(error)
        else:
            # Use severity assessor to infer category for regular exceptions
            category = self.severity_assessor._infer_category_from_exception(error)

        # Create SmartError
        smart_error = SmartError(
            message=str(error), category=category, severity=severity, context=context or {}, source_exception=error
        )

        # Generate suggestions
        suggestions = self.suggestion_engine.generate_suggestions(smart_error)
        for suggestion in suggestions:
            smart_error.add_suggestion(suggestion)

        return smart_error

    def _map_migration_error_to_category(self, error: MigrationError) -> ErrorCategory:
        """Map existing MigrationError types to ErrorCategory."""
        if isinstance(error, ParseError):
            return ErrorCategory.PARSING
        elif isinstance(error, TransformationError):
            return ErrorCategory.TRANSFORMATION
        elif isinstance(error, ValidationError):
            return ErrorCategory.VALIDATION
        elif isinstance(error, ConfigurationError):
            return ErrorCategory.CONFIGURATION

        return ErrorCategory.UNKNOWN

    def get_recovery_workflow(self, error: SmartError) -> RecoveryWorkflow | None:
        """Get the most appropriate recovery workflow for an error."""
        return self.recovery_assistant.suggest_recovery_workflow(error)

    def report_error(
        self, error: Exception, context: dict[str, Any] | None = None, include_workflow: bool = True
    ) -> dict[str, Any]:
        """Generate comprehensive error report with suggestions and recovery info."""
        smart_error = self.enhance_error(error, context)

        report = {
            "error": {
                "message": smart_error.message,
                "category": smart_error.category.value,
                "severity": smart_error.severity.value,
                "context": smart_error.context,
                "suggestions": [s.to_dict() for s in smart_error.get_prioritized_suggestions()],
                "recovery_actions": smart_error.recovery_actions,
                "is_recoverable": smart_error.is_recoverable(),
            }
        }

        if include_workflow:
            workflow = self.get_recovery_workflow(smart_error)
            if workflow:
                report["recovery_workflow"] = workflow.to_dict()

        return report


# Import here to avoid circular imports
try:
    from .exceptions import ConfigurationError, ParseError, TransformationError, ValidationError
except ImportError:
    # Handle case where exceptions aren't available yet
    ParseError = None  # type: ignore
    TransformationError = None  # type: ignore
    ValidationError = None  # type: ignore
    ConfigurationError = None  # type: ignore
