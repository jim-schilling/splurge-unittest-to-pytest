"""Enhanced error reporting utilities for transformation debugging.

This module provides structured error reporting that preserves context and provides
actionable debugging information for transformation failures.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import logging
import traceback
from dataclasses import dataclass, field
from typing import Any

from ..exceptions import TransformationError


@dataclass(frozen=True)
class ErrorContext:
    """Context information for debugging transformation errors."""

    component: str
    """The component where the error occurred (e.g., 'assert_transformer')"""

    operation: str
    """The operation being performed (e.g., 'transform_assert_equal')"""

    source_file: str | None = None
    """The source file being processed"""

    line_number: int | None = None
    """The line number where the error occurred"""

    node_type: str | None = None
    """The AST node type being processed"""

    additional_context: dict[str, Any] = field(default_factory=dict)
    """Additional context-specific information"""


@dataclass
class TransformationErrorDetails:
    """Detailed information about a transformation error."""

    error: Exception
    """The original exception that occurred"""

    context: ErrorContext
    """Context information about where and why the error occurred"""

    severity: str = "ERROR"
    """Error severity level (ERROR, WARNING, INFO)"""

    suggestions: list[str] = field(default_factory=list)
    """Suggested actions for resolving the error"""

    stack_trace: str | None = None
    """Stack trace if available"""

    def __post_init__(self) -> None:
        """Capture stack trace if not provided."""
        if self.stack_trace is None:
            self.stack_trace = traceback.format_exc()


class ErrorReporter:
    """Centralized error reporting for transformation issues."""

    def __init__(self, logger_name: str = "splurge_unittest_to_pytest") -> None:
        """Initialize the error reporter.

        Args:
            logger_name: Name of the logger to use for error reporting
        """
        self.logger = logging.getLogger(logger_name)
        self._error_history: list[TransformationErrorDetails] = []

    def report_error(
        self, error: Exception, context: ErrorContext, severity: str = "ERROR", suggestions: list[str] | None = None
    ) -> TransformationErrorDetails:
        """Report a transformation error with context.

        Args:
            error: The exception that occurred
            context: Context information about the error
            severity: Error severity level
            suggestions: Optional list of suggested fixes

        Returns:
            TransformationErrorDetails containing all error information
        """
        error_details = TransformationErrorDetails(
            error=error, context=context, severity=severity, suggestions=suggestions or []
        )

        self._error_history.append(error_details)
        self._log_error(error_details)

        return error_details

    def _log_error(self, error_details: TransformationErrorDetails) -> None:
        """Log the error with appropriate level and formatting."""
        message = self._format_error_message(error_details)

        if error_details.severity == "ERROR":
            self.logger.error(message)
        elif error_details.severity == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def _format_error_message(self, error_details: TransformationErrorDetails) -> str:
        """Format a detailed error message."""
        context = error_details.context

        message_parts = [f"[{context.component}] {context.operation} failed"]

        if context.source_file:
            message_parts.append(f"in {context.source_file}")

        if context.line_number:
            message_parts.append(f"at line {context.line_number}")

        if context.node_type:
            message_parts.append(f"while processing {context.node_type}")

        message_parts.append(f": {error_details.error}")

        if error_details.suggestions:
            message_parts.append(f" Suggestions: {'; '.join(error_details.suggestions)}")

        return "".join(message_parts)

    def get_error_history(self) -> list[TransformationErrorDetails]:
        """Get the history of reported errors.

        Returns:
            List of all error details reported so far
        """
        return self._error_history.copy()

    def clear_error_history(self) -> None:
        """Clear the error history."""
        self._error_history.clear()

    def get_error_summary(self) -> dict[str, int]:
        """Get a summary of error types and counts.

        Returns:
            Dictionary mapping error types to counts
        """
        summary: dict[str, int] = {}
        for error_detail in self._error_history:
            error_type = type(error_detail.error).__name__
            summary[error_type] = summary.get(error_type, 0) + 1
        return summary


# Global error reporter instance
_global_reporter = ErrorReporter()


def get_error_reporter() -> ErrorReporter:
    """Get the global error reporter instance.

    Returns:
        The global ErrorReporter instance
    """
    return _global_reporter


def report_transformation_error(
    error: Exception,
    component: str,
    operation: str,
    source_file: str | None = None,
    line_number: int | None = None,
    node_type: str | None = None,
    additional_context: dict[str, Any] | None = None,
    severity: str = "ERROR",
    suggestions: list[str] | None = None,
) -> TransformationErrorDetails:
    """Convenience function to report transformation errors.

    Args:
        error: The exception that occurred
        component: Component name (e.g., 'assert_transformer')
        operation: Operation name (e.g., 'transform_assert_equal')
        source_file: Source file being processed
        line_number: Line number where error occurred
        node_type: AST node type being processed
        additional_context: Additional context information
        severity: Error severity level
        suggestions: Suggested fixes

    Returns:
        TransformationErrorDetails with all error information
    """
    context = ErrorContext(
        component=component,
        operation=operation,
        source_file=source_file,
        line_number=line_number,
        node_type=node_type,
        additional_context=additional_context or {},
    )

    return get_error_reporter().report_error(error=error, context=context, severity=severity, suggestions=suggestions)


def create_transformation_error(
    message: str,
    component: str,
    operation: str,
    source_file: str | None = None,
    line_number: int | None = None,
    node_type: str | None = None,
    additional_context: dict[str, Any] | None = None,
) -> TransformationError:
    """Create a TransformationError with enhanced context.

    Args:
        message: Error message
        component: Component name
        operation: Operation name
        source_file: Source file being processed
        line_number: Line number where error occurred
        node_type: AST node type being processed
        additional_context: Additional context information

    Returns:
        TransformationError with context information
    """
    context = ErrorContext(
        component=component,
        operation=operation,
        source_file=source_file,
        line_number=line_number,
        node_type=node_type,
        additional_context=additional_context or {},
    )

    # Report the error to get detailed information
    error_details = report_transformation_error(
        error=Exception(message),
        component=component,
        operation=operation,
        source_file=source_file,
        line_number=line_number,
        node_type=node_type,
        additional_context=additional_context,
    )

    return TransformationError(message=message, context=context, suggestions=error_details.suggestions)
