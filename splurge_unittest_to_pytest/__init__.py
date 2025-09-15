"""Splurge unittest to pytest converter.

A Python library for converting unittest-style tests to modern pytest-style tests.
"""

__version__ = "2025.1.1"
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

DOMAINS = ["core"]

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

# Canonical domain names (small, stable set)
__domains__: list[str] = [
    "assertions",
    "batch",
    "bundles",
    "cli",
    "converter",
    "core",
    "diagnostics",
    "exceptions",
    "fixtures",
    "general",
    "generator",
    "goldens",
    "helpers",
    "imports",
    "integration",
    "literals",
    "main",
    "manager",
    "miscmocks",
    "naming",
    "parameters",
    "patch",
    "pipeline",
    "regex",
    "rewriter",
    "smoke",
    "stages",
    "teardown",
    "tidy",
    "transform",
    "validation",
]

# Associated domains for this module
# Moved to top-level after imports for discoverability.
