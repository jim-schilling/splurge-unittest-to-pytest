"""Top-level package for the splurge unittest -> pytest converter.

Provides the public package metadata and re-exports the primary
conversion helpers and exception types for convenient import by
callers.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

__version__ = "2025.3.3"
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
