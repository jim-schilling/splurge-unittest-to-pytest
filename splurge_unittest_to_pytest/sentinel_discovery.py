"""Discovery helpers for identifying unittest-style test files.

This module centralizes fast (textual) and AST-based discovery probes so the
CLI and file discovery utilities can reuse the same logic.
"""

from pathlib import Path

from .exceptions import EncodingError, PermissionDeniedError
from .exceptions import FileNotFoundError as SplurgeFileNotFoundError

DOMAINS = ["discovery"]


def is_unittest_file(file_path: str | Path, *, fast_discovery: bool = False) -> bool:
    """Return True if a file appears to contain unittest-style tests.

    Args:
        file_path: Path to the Python file.
        fast_discovery: When True, only use textual heuristics; when False,
            probe the AST for stronger signals.
    """
    file_path = Path(file_path)

    try:
        if not file_path.exists():
            raise SplurgeFileNotFoundError(f"Input file not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")

        # Skip files that are already using pytest
        if "import pytest" in content or "from pytest" in content:
            return False

        # Fast discovery: textual heuristics
        if fast_discovery:
            unittest_indicators = [
                "import unittest",
                "from unittest import",
                "unittest.TestCase",
                "class Test",
                "def test_",
                "setUp(",
                "tearDown(",
                "self.assert",
            ]
            return any(indicator in content for indicator in unittest_indicators)

        # AST-based probe
        try:
            import ast

            tree = ast.parse(content)

            found_testcase = False
            found_test_fn = False
            found_assert_usage = False

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        try:
                            if isinstance(base, ast.Attribute) and getattr(base, "attr", "") == "TestCase":
                                found_testcase = True
                            elif isinstance(base, ast.Name) and base.id == "TestCase":
                                found_testcase = True
                        except Exception:
                            pass
                    if node.name.startswith("Test"):
                        found_testcase = True

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("test_"):
                        found_test_fn = True

                if isinstance(node, ast.Attribute):
                    try:
                        if (
                            isinstance(node.value, ast.Name)
                            and node.value.id == "self"
                            and isinstance(node.attr, str)
                            and node.attr.startswith("assert")
                        ):
                            found_assert_usage = True
                    except Exception:
                        pass

            if found_testcase or found_test_fn or found_assert_usage:
                return True
        except Exception:
            # fallback to textual heuristics
            pass

        unittest_indicators = [
            "import unittest",
            "from unittest import",
            "unittest.TestCase",
            "class Test",
            "def test_",
            "setUp(",
            "tearDown(",
            "self.assert",
        ]
        return any(indicator in content for indicator in unittest_indicators)

    except PermissionError:
        raise PermissionDeniedError(f"Permission denied reading file: {file_path}") from PermissionError
    except UnicodeDecodeError as e:
        raise EncodingError(f"Failed to decode file with UTF-8 encoding: {file_path}") from e
