"""Splurge unittest to pytest converter.

A Python library for converting unittest-style tests to modern pytest-style tests.
"""

__version__ = "2025.1.0"
__author__ = "Jim Schilling"

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
