"""Splurge unittest to pytest converter.

A Python library for converting unittest-style tests to modern pytest-style tests.
"""

__version__ = "2025.0.1"
__author__ = "Jim Schilling"

# Legacy transformer is deprecated and no longer exported. Use the staged
# pipeline via `convert_string` or `PatternConfigurator` from `main`.
from splurge_unittest_to_pytest.exceptions import (
    BackupError,
    ConversionError,
    EncodingError,
    FileNotFoundError,
    FileOperationError,
    ParseError,
    PermissionDeniedError,
    SplurgeError,
)
from splurge_unittest_to_pytest.main import convert_file, convert_string, ConversionResult

__all__ = [
    # legacy transformer removed
    "convert_file",
    "convert_string",
    "ConversionResult",
    "BackupError",
    "ConversionError",
    "EncodingError",
    "FileNotFoundError",
    "FileOperationError",
    "ParseError",
    "PermissionDeniedError",
    "SplurgeError",
]