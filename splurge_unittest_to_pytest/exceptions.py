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
    """

    def __init__(self, message: str, pattern_type: str | None = None, node_type: str | None = None):
        details: dict[str, Any] = {}
        if pattern_type:
            details["pattern_type"] = pattern_type
        if node_type:
            details["node_type"] = node_type
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
