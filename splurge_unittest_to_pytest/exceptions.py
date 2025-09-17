"""Domain-specific exceptions used across the package.

This module defines a small hierarchy of exceptions used by the
converter and CLI code. The hierarchy is intentionally shallow so
callers can catch broad categories (for example ``SplurgeError``) or
more specific failures (for example ``ParseError``).

Exceptions:
    SplurgeError: Base class for all package-specific errors.
    ConversionError: Conversion-specific failures.
    ParseError: Raised when source code parsing fails.
    FileOperationError: File operation related errors (I/O, encoding,
        permissions).
    FileNotFoundError: Input file not found.
    PermissionDeniedError: Permission issues while operating on files.
    EncodingError: Encoding-related file errors.
    BackupError: Failures relating to backup operations.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

DOMAINS = ["exceptions"]

# Associated domains for this module
# Moved to top of module after imports.


class SplurgeError(Exception):
    """Base exception for all splurge-related errors."""

    pass


class ConversionError(SplurgeError):
    """Raised when unittest to pytest conversion fails."""

    pass


class ParseError(ConversionError):
    """Raised when source code cannot be parsed."""

    pass


class FileOperationError(SplurgeError):
    """Raised when file operations fail."""

    pass


class FileNotFoundError(FileOperationError):
    """Raised when input file is not found."""

    pass


class PermissionDeniedError(FileOperationError):
    """Raised when file permissions prevent operation."""

    pass


class EncodingError(FileOperationError):
    """Raised when file encoding issues occur."""

    pass


class BackupError(FileOperationError):
    """Raised when backup operations fail."""

    pass
