"""Domain-specific exceptions for splurge-unittest-to-pytest."""

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
