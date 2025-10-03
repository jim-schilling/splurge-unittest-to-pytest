"""Custom exception classes for the unittest-to-pytest migration tool.

This module defines a small hierarchy of exceptions used by the
migration pipeline. Each exception carries an optional ``details``
mapping that contains structured context (for example source file and
location) to help callers diagnose failures programmatically.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from typing import Any


class MigrationError(Exception):
    """Base exception for migration-related errors.

    Args:
        message: Human-readable error message.
        details: Optional mapping with structured diagnostic data.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ParseError(MigrationError):
    """Raised when parsing of source code fails.

    Args:
        message: Error message describing the parse failure.
        source_file: Path to the file being parsed.
        line: Optional line number where the error occurred.
        column: Optional column offset where the error occurred.
    """

    def __init__(self, message: str, source_file: str, line: int | None = None, column: int | None = None):
        details: dict[str, Any] = {"source_file": source_file}
        if line is not None:
            details["line"] = line
        if column is not None:
            details["column"] = column
        super().__init__(message, details)


class TransformationError(MigrationError):
    """Raised when a transformation step cannot be applied.

    Args:
        message: Human-readable description of the failure.
        pattern_type: Optional transformation pattern identifier.
        node_type: Optional AST/CST node type that caused the error.
        context: Optional ErrorContext for enhanced debugging information.
        suggestions: Optional list of suggested fixes.
    """

    def __init__(
        self,
        message: str,
        pattern_type: str | None = None,
        node_type: str | None = None,
        context: Any | None = None,
        suggestions: list[str] | None = None,
    ):
        details: dict[str, Any] = {}
        if pattern_type:
            details["pattern_type"] = pattern_type
        if node_type:
            details["node_type"] = node_type
        if context:
            details["context"] = context
        if suggestions:
            details["suggestions"] = suggestions
        super().__init__(message, details)


class ValidationError(MigrationError):
    """Raised when input or configuration validation fails.

    Args:
        message: Description of the validation failure.
        validation_type: Identifier for the kind of validation performed.
        field: Optional field name that failed validation.
    """

    def __init__(self, message: str, validation_type: str, field: str | None = None):
        details: dict[str, Any] = {"validation_type": validation_type}
        if field:
            details["field"] = field
        super().__init__(message, details)


class ConfigurationError(MigrationError):
    """Raised when an application configuration is invalid.

    Args:
        message: Human readable description of the configuration problem.
        config_key: Optional configuration key that caused the error.
    """

    def __init__(self, message: str, config_key: str | None = None):
        details: dict[str, Any] = {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details)


class DecisionAnalysisError(MigrationError):
    """Base exception for decision analysis errors.

    Args:
        message: Human-readable error message.
        analysis_step: Optional step where the error occurred.
        function_name: Optional function being analyzed.
        class_name: Optional class being analyzed.
        module_name: Optional module being analyzed.
    """

    def __init__(
        self,
        message: str,
        analysis_step: str | None = None,
        function_name: str | None = None,
        class_name: str | None = None,
        module_name: str | None = None,
    ):
        details: dict[str, Any] = {}
        if analysis_step:
            details["analysis_step"] = analysis_step
        if function_name:
            details["function_name"] = function_name
        if class_name:
            details["class_name"] = class_name
        if module_name:
            details["module_name"] = module_name
        # Initialize parent with message and complete details
        super().__init__(message)
        self.details = details


class AnalysisStepError(DecisionAnalysisError):
    """Raised when an analysis step fails to execute.

    Args:
        message: Description of the step failure.
        analysis_step: Name of the step that failed.
        function_name: Optional function being analyzed when the error occurred.
        class_name: Optional class being analyzed when the error occurred.
        module_name: Optional module being analyzed when the error occurred.
    """

    def __init__(
        self,
        message: str,
        analysis_step: str,
        function_name: str | None = None,
        class_name: str | None = None,
        module_name: str | None = None,
    ):
        # Build complete details dict including parent class fields
        details: dict[str, Any] = {"analysis_step": analysis_step}
        if function_name:
            details["function_name"] = function_name
        if class_name:
            details["class_name"] = class_name
        if module_name:
            details["module_name"] = module_name
        # Initialize parent with message and complete details
        super().__init__(message)
        self.details = details


class PatternDetectionError(DecisionAnalysisError):
    """Raised when pattern detection fails for a specific construct.

    Args:
        message: Description of the pattern detection failure.
        pattern_type: Type of pattern that failed to be detected.
        function_name: Function where the pattern detection failed.
        class_name: Class containing the function.
        module_name: Module containing the class.
    """

    def __init__(
        self,
        message: str,
        pattern_type: str,
        function_name: str | None = None,
        class_name: str | None = None,
        module_name: str | None = None,
    ):
        # Build complete details dict including parent class fields
        details: dict[str, Any] = {"pattern_type": pattern_type}
        if function_name:
            details["function_name"] = function_name
        if class_name:
            details["class_name"] = class_name
        if module_name:
            details["module_name"] = module_name
        # Initialize parent with message and complete details
        super().__init__(message)
        self.details = details


class ReconciliationError(DecisionAnalysisError):
    """Raised when proposal reconciliation fails.

    Args:
        message: Description of the reconciliation failure.
        conflict_type: Type of conflict that couldn't be resolved.
        class_name: Class where the reconciliation failed.
        module_name: Module containing the class.
    """

    def __init__(self, message: str, conflict_type: str, class_name: str | None = None, module_name: str | None = None):
        # Build complete details dict including parent class fields
        details: dict[str, Any] = {"conflict_type": conflict_type}
        if class_name:
            details["class_name"] = class_name
        if module_name:
            details["module_name"] = module_name
        # Initialize parent with message and complete details
        super().__init__(message)
        self.details = details


class ContextError(DecisionAnalysisError):
    """Raised when required context or metadata is missing.

    Args:
        message: Description of the missing context.
        required_context: Type of context that was expected.
        analysis_step: Step that required the missing context.
    """

    def __init__(self, message: str, required_context: str, analysis_step: str | None = None):
        # Build complete details dict including parent class fields
        details: dict[str, Any] = {"required_context": required_context}
        if analysis_step:
            details["analysis_step"] = analysis_step
        # Initialize parent with message and complete details
        super().__init__(message)
        self.details = details


class TransformationValidationError(TransformationError):
    """Raised when the final transformed code fails CST validation.

    This exception is raised during the final validation phase of transformation
    to ensure that generated code can be successfully parsed by libcst.
    """

    def __init__(self, message: str):
        super().__init__(message, pattern_type="validation")


class ParametrizeConversionError(TransformationError):
    """Raised when a subTest loop cannot be safely converted to parametrize.

    This exception indicates that the subTest pattern in the source code cannot
    be automatically converted to pytest.mark.parametrize due to structural
    or semantic complexities.
    """

    def __init__(self, message: str = "Cannot safely convert subTest loop to parametrize"):
        super().__init__(message, pattern_type="parametrize")
