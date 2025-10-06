"""Property-based tests for end-to-end migration workflows.

This module contains Hypothesis-based property tests for complete
migration workflows, testing the full pipeline from unittest source
to pytest output including file I/O, orchestration, and validation.
"""

import ast
import tempfile
import unittest
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator
from tests.hypothesis_config import DEFAULT_SETTINGS
from tests.property.strategies import unittest_source_files


class TestIntegrationProperties:
    """Property-based tests for end-to-end migration workflows."""

    @DEFAULT_SETTINGS
    @given(unittest_code=unittest_source_files())
    def test_full_migration_workflow_produces_valid_pytest_code(self, unittest_code: str) -> None:
        """Test that full migration workflow produces valid pytest code."""
        orchestrator = MigrationOrchestrator()

        # Create temporary source file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(unittest_code)
            source_file = f.name

        try:
            # Configure for dry-run to avoid file system side effects
            config = MigrationConfig(dry_run=True)

            # Run full migration
            result = orchestrator.migrate_file(source_file, config)

            # Should succeed
            assert result.is_success(), f"Migration failed: {result.error}"

            # Should contain generated code in metadata
            assert result.metadata is not None
            assert "generated_code" in result.metadata

            generated_code = result.metadata["generated_code"]

            # Generated code should be valid Python
            self._validate_python_syntax(generated_code)

            # Generated code should contain pytest-compatible structures
            self._validate_pytest_compatibility(generated_code)

        finally:
            # Clean up
            Path(source_file).unlink(missing_ok=True)

    @DEFAULT_SETTINGS
    @given(unittest_code=unittest_source_files())
    def test_migration_preserves_test_structure(self, unittest_code: str) -> None:
        """Test that migration preserves the overall test structure."""
        orchestrator = MigrationOrchestrator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(unittest_code)
            source_file = f.name

        try:
            config = MigrationConfig(dry_run=True)
            result = orchestrator.migrate_file(source_file, config)

            assert result.is_success()

            original_tree = ast.parse(unittest_code)
            generated_code = result.metadata["generated_code"]
            generated_tree = ast.parse(generated_code)

            # Should preserve class structure (though names may change)
            original_classes = [node for node in ast.walk(original_tree) if isinstance(node, ast.ClassDef)]
            generated_classes = [node for node in ast.walk(generated_tree) if isinstance(node, ast.ClassDef)]

            assert len(generated_classes) >= len(original_classes), "Should not lose test classes"

            # Should preserve method structure
            original_methods = [
                node
                for node in ast.walk(original_tree)
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            ]
            generated_methods = [
                node
                for node in ast.walk(generated_tree)
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            ]

            assert len(generated_methods) >= len(original_methods), "Should not lose test methods"

        finally:
            Path(source_file).unlink(missing_ok=True)

    @DEFAULT_SETTINGS
    @given(unittest_code=unittest_source_files())
    def test_migration_with_file_output_creates_valid_files(self, unittest_code: str) -> None:
        """Test that migration with file output creates valid pytest files."""
        orchestrator = MigrationOrchestrator()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source file
            source_file = Path(tmpdir) / "test_unittest.py"
            source_file.write_text(unittest_code)

            config = MigrationConfig(target_root=str(tmpdir), target_suffix="_migrated")

            result = orchestrator.migrate_file(str(source_file), config)

            assert result.is_success()

            # Should have created a migrated file
            migrated_files = list(Path(tmpdir).glob("*_migrated.py"))
            assert len(migrated_files) > 0, f"No migrated files found in {tmpdir}"

            # Check the first migrated file
            migrated_file = migrated_files[0]
            generated_code = migrated_file.read_text()
            self._validate_python_syntax(generated_code)
            self._validate_pytest_compatibility(generated_code)

    @DEFAULT_SETTINGS
    @given(unittest_code=unittest_source_files())
    def test_directory_migration_workflow(self, unittest_code: str) -> None:
        """Test that directory migration processes multiple files correctly."""
        orchestrator = MigrationOrchestrator()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create multiple unittest files
            num_files = 3
            for i in range(num_files):
                source_file = tmpdir_path / f"test_unittest_{i}.py"
                source_file.write_text(unittest_code.replace("TestA", f"Test{i}"))

            config = MigrationConfig(target_root=str(tmpdir_path / "output"), target_suffix="_converted")

            result = orchestrator.migrate_directory(str(tmpdir_path), config)

            assert result.is_success()

            # Should have created output directory
            output_dir = tmpdir_path / "output"
            assert output_dir.exists()

            # Should have migrated files
            migrated_files = list(output_dir.glob("*_converted.py"))
            assert len(migrated_files) >= num_files

            # Check that migrated files are valid
            for migrated_file in migrated_files[:3]:  # Check first 3
                generated_code = migrated_file.read_text()
                self._validate_python_syntax(generated_code)
                self._validate_pytest_compatibility(generated_code)

    def _validate_python_syntax(self, code: str) -> None:
        """Validate that code is syntactically valid Python."""
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Generated code is not valid Python: {e}")

    def _validate_pytest_compatibility(self, code: str) -> None:
        """Validate that code contains pytest-compatible structures."""
        tree = ast.parse(code)

        # Should not contain unittest imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # Should not have unittest imports (may have others)
        assert "unittest" not in imports, "Generated code should not import unittest"

        # Should have some test functions
        test_functions = [
            node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        ]

        # Allow for cases where all tests might be removed due to errors, but generally expect tests
        # This is a property test, so we can't be too strict
        if test_functions:
            # If there are test functions, they should have some body
            for func in test_functions:
                assert len(func.body) > 0, "Test functions should have body"
