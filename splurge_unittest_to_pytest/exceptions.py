"""Custom exception classes for the unittest-to-pytest migration tool."""

from typing import Any


class MigrationError(Exception):
    """Base exception for migration-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ParseError(MigrationError):
    """Exception raised when source code parsing fails."""

    def __init__(self, message: str, source_file: str, line: int | None = None, column: int | None = None):
        details: dict[str, Any] = {"source_file": source_file}
        if line is not None:
            details["line"] = line
        if column is not None:
            details["column"] = column
        super().__init__(message, details)


class TransformationError(MigrationError):
    """Exception raised when code transformation fails."""

    def __init__(self, message: str, pattern_type: str | None = None, node_type: str | None = None):
        details: dict[str, Any] = {}
        if pattern_type:
            details["pattern_type"] = pattern_type
        if node_type:
            details["node_type"] = node_type
        super().__init__(message, details)


class ValidationError(MigrationError):
    """Exception raised when validation fails."""

    def __init__(self, message: str, validation_type: str, field: str | None = None):
        details: dict[str, Any] = {"validation_type": validation_type}
        if field:
            details["field"] = field
        super().__init__(message, details)


class ConfigurationError(MigrationError):
    """Exception raised when configuration is invalid."""

    def __init__(self, message: str, config_key: str | None = None):
        details: dict[str, Any] = {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details)
