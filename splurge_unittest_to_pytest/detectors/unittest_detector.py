"""AST-based unittest file detection.

This module provides robust detection of unittest files using AST analysis
instead of string heuristics. It eliminates false positives and negatives
by actually parsing Python code and looking for structural unittest patterns.
"""

from __future__ import annotations

import ast
from pathlib import Path


class UnittestFileDetector(ast.NodeVisitor):
    """AST visitor that detects unittest files through structural analysis.

    This detector identifies unittest files by checking for:
    1. Classes that inherit from unittest.TestCase
    2. Import statements that bring in unittest
    3. Method calls to unittest assertion methods

    Only files that meet multiple criteria are considered unittest files,
    eliminating false positives from string-based detection.
    """

    def __init__(self) -> None:
        self.has_unittest_import = False
        self.has_testcase_inheritance = False
        self.has_assertion_calls = False
        self._current_class_bases: list[str] = []

    def is_unittest_file(self, file_path: str | Path) -> bool:
        """Check if a file contains unittest code using AST analysis.

        Args:
            file_path: Path to the Python file to analyze.

        Returns:
            True if the file contains unittest patterns, False otherwise.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            UnicodeDecodeError: If the file can't be decoded as UTF-8.
            SyntaxError: If the file contains invalid Python syntax.
        """
        file_path = Path(file_path)

        # Read and parse the file
        try:
            with open(file_path, encoding="utf-8") as f:
                source_code = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}") from None
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(
                e.encoding, e.object, e.start, e.end, f"Cannot decode file {file_path} as UTF-8"
            ) from e

        try:
            tree = ast.parse(source_code, filename=str(file_path))
        except SyntaxError as e:
            raise SyntaxError(f"Invalid Python syntax in {file_path}") from e

        # Reset state and visit the AST
        self.has_unittest_import = False
        self.has_testcase_inheritance = False
        self.has_assertion_calls = False

        self.visit(tree)

        # Require multiple indicators to avoid false positives
        # Must have unittest imports AND (TestCase inheritance OR assertion calls)
        has_imports = self.has_unittest_import
        has_structure = self.has_testcase_inheritance or self.has_assertion_calls

        return has_imports and has_structure

    def visit_Import(self, node: ast.Import) -> None:
        """Check for 'import unittest' statements."""
        for alias in node.names:
            if alias.name == "unittest":
                self.has_unittest_import = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for 'from unittest import ...' statements."""
        if node.module == "unittest":
            self.has_unittest_import = True
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check if any class inherits from unittest.TestCase."""
        # Store current class bases for method analysis
        self._current_class_bases = []
        for base in node.bases:
            base_name = self._get_full_name(base)
            if base_name:
                self._current_class_bases.append(base_name)
                if base_name in ("unittest.TestCase", "TestCase"):
                    self.has_testcase_inheritance = True

        self.generic_visit(node)
        self._current_class_bases = []

    def visit_Call(self, node: ast.Call) -> None:
        """Check for unittest assertion method calls."""
        if isinstance(node.func, ast.Attribute):
            # Check for self.assert* calls (common unittest pattern)
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
                and node.func.attr.startswith("assert")
            ):
                self.has_assertion_calls = True

        self.generic_visit(node)

    def _is_in_testcase_class(self) -> bool:
        """Check if we're currently inside a TestCase class definition."""
        return any("TestCase" in base for base in self._current_class_bases)

    def _get_full_name(self, node: ast.AST) -> str | None:
        """Get the full dotted name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            prefix = self._get_full_name(node.value)
            if prefix:
                return f"{prefix}.{node.attr}"
        return None
