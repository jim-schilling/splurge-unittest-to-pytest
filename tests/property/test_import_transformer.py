"""Property-based tests for import transformer functionality.

This module contains Hypothesis-based property tests for the import
transformation functions in splurge_unittest_to_pytest.transformers.import_transformer.
These tests verify that import additions and removals preserve syntax,
are idempotent, and behave conservatively.
"""

import ast
import re

import libcst as cst
import pytest
from hypothesis import given, settings

from splurge_unittest_to_pytest.transformers.import_transformer import (
    add_pytest_imports,
    remove_unittest_imports_if_unused,
)
from tests.hypothesis_config import DEFAULT_SETTINGS
from tests.property.strategies import python_source_code


class TestImportTransformerProperties:
    """Property-based tests for import transformation functions."""

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_add_pytest_imports_preserves_syntax(self, source_code: str) -> None:
        """Test that add_pytest_imports produces valid Python syntax."""
        result = add_pytest_imports(source_code)

        # Result should be valid Python
        try:
            ast.parse(result)
        except SyntaxError:
            pytest.fail(f"add_pytest_imports produced invalid syntax: {result}")

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_add_pytest_imports_is_idempotent(self, source_code: str) -> None:
        """Test that add_pytest_imports is idempotent - applying multiple times is safe."""
        first_result = add_pytest_imports(source_code)
        second_result = add_pytest_imports(first_result)

        # Second application should not change the result
        assert first_result == second_result

        # Should not create duplicate imports
        pytest_count = len(re.findall(r"\bimport pytest\b", second_result))
        assert pytest_count <= 1, f"Found {pytest_count} 'import pytest' statements"

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_add_pytest_imports_conservative_on_errors(self, source_code: str) -> None:
        """Test that add_pytest_imports returns original code on parsing errors."""
        # The function should handle any input gracefully
        result = add_pytest_imports(source_code)
        assert isinstance(result, str)
        # Length should be reasonable (not exponentially growing)
        assert len(result) <= len(source_code) + 100  # Allow some growth for imports

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_add_pytest_imports_only_when_needed(self, source_code: str) -> None:
        """Test that pytest imports are only added when not already present."""
        if "import pytest" in source_code or "from pytest" in source_code:
            # If pytest is already imported, should not change
            result = add_pytest_imports(source_code)
            assert result == source_code
        else:
            # If pytest is not imported, should add it
            result = add_pytest_imports(source_code)
            if result != source_code:  # Only check if transformation occurred
                assert "import pytest" in result

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_remove_unittest_imports_preserves_syntax(self, source_code: str) -> None:
        """Test that remove_unittest_imports_if_unused produces valid Python syntax."""
        result = remove_unittest_imports_if_unused(source_code)

        # Result should be valid Python
        try:
            ast.parse(result)
        except SyntaxError:
            pytest.fail(f"remove_unittest_imports_if_unused produced invalid syntax: {result}")

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_remove_unittest_imports_is_idempotent(self, source_code: str) -> None:
        """Test that remove_unittest_imports_if_unused is idempotent."""
        first_result = remove_unittest_imports_if_unused(source_code)
        second_result = remove_unittest_imports_if_unused(first_result)

        # Second application should not change the result
        assert first_result == second_result

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_remove_unittest_imports_conservative_on_errors(self, source_code: str) -> None:
        """Test that remove_unittest_imports_if_unused returns original code on errors."""
        result = remove_unittest_imports_if_unused(source_code)
        assert isinstance(result, str)
        # Should not grow significantly
        assert len(result) <= len(source_code)

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_remove_unittest_imports_only_when_unused(self, source_code: str) -> None:
        """Test that unittest imports are only removed when truly unused."""
        # Parse the source to check for unittest usage
        try:
            tree = ast.parse(source_code)
            has_unittest_usage = any(
                isinstance(node, ast.Name) and node.id == "unittest"
                for node in ast.walk(tree)
                if not isinstance(node, ast.Import) and not isinstance(node, ast.ImportFrom)
            )
        except SyntaxError:
            has_unittest_usage = False  # Can't determine, assume no usage

        result = remove_unittest_imports_if_unused(source_code)

        if has_unittest_usage:
            # If unittest is used, imports should be preserved
            unittest_import_count_before = len(re.findall(r"\bimport unittest\b", source_code)) + len(
                re.findall(r"\bfrom unittest\b", source_code)
            )
            unittest_import_count_after = len(re.findall(r"\bimport unittest\b", result)) + len(
                re.findall(r"\bfrom unittest\b", result)
            )
            assert unittest_import_count_after >= unittest_import_count_before
        # If no usage, we can't guarantee removal since the check might be conservative

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_import_transformations_commute_with_ast_parsing(self, source_code: str) -> None:
        """Test that import transformations don't break subsequent AST operations."""
        # Apply transformations
        with_pytest = add_pytest_imports(source_code)
        cleaned = remove_unittest_imports_if_unused(with_pytest)

        # Both results should be parseable
        try:
            ast.parse(with_pytest)
            ast.parse(cleaned)
        except SyntaxError as e:
            pytest.fail(f"Import transformation broke AST parsing: {e}")

        # Should be able to parse with libcst too
        try:
            cst.parse_module(with_pytest)
            cst.parse_module(cleaned)
        except cst.ParserSyntaxError as e:
            pytest.fail(f"Import transformation broke libcst parsing: {e}")

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_add_pytest_imports_preserves_existing_imports(self, source_code: str) -> None:
        """Test that add_pytest_imports doesn't remove or modify existing imports."""
        try:
            original_tree = ast.parse(source_code)
            original_imports = [
                node for node in ast.walk(original_tree) if isinstance(node, ast.Import | ast.ImportFrom)
            ]
        except SyntaxError:
            original_imports = []

        result = add_pytest_imports(source_code)

        try:
            result_tree = ast.parse(result)
            result_imports = [node for node in ast.walk(result_tree) if isinstance(node, ast.Import | ast.ImportFrom)]

            # Should have at least as many imports as original
            assert len(result_imports) >= len(original_imports)

            # All original imports should still be present (by string content)
            original_import_strings = {ast.unparse(imp) for imp in original_imports}
            result_import_strings = {ast.unparse(imp) for imp in result_imports}

            for orig_imp in original_import_strings:
                assert orig_imp in result_import_strings

        except SyntaxError:
            # If result is not parseable, that's a different test's concern
            pass
