"""Test cases for deeply nested control flow structures."""

from pathlib import Path

import pytest

from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


class TestDeeplyNestedControlFlow:
    """Test transformation of deeply nested control flow structures."""

    def test_deeply_nested_try_with_blocks(self):
        """Test that deeply nested try/with blocks with asserts can be processed without errors."""
        test_file = Path(__file__).parent.parent / "data" / "complex_nesting" / "deeply_nested_control_flow.txt"

        # Read the test file
        with open(test_file, encoding="utf-8") as f:
            source_code = f.read()

        # Create transformer
        transformer = UnittestToPytestCstTransformer()

        # This should not raise any exceptions, even with the complex nesting
        result = transformer.transform_code(source_code)

        # Verify we got some result (transformation may or may not change the code,
        # but it should complete without errors)
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify the basic structure is preserved (transformed imports, class definition, method names)
        assert "from unittest.mock import Mock, patch" in result
        assert "import pytest" in result
        assert "class TestDeeplyNestedControlFlow" in result
        assert "def test_deeply_nested_try_with_assert" in result
        assert "def test_mixed_nesting_patterns" in result
        assert "def test_complex_error_handling_nesting" in result

        # Verify that the deeply nested structure didn't break the transformation
        assert "try:" in result  # Should still have try blocks
        assert "with " in result  # Should still have with blocks
        assert "assert " in result  # Should still have assert statements

    def test_extremely_deep_nesting_robustness(self):
        """Test that the _safe_extract_statements function handles pathological cases."""
        from splurge_unittest_to_pytest.transformers.assert_transformer import _safe_extract_statements

        # Test with None input
        assert _safe_extract_statements(None) is None

        # Test with object that doesn't have body attribute
        class MockObject:
            pass

        assert _safe_extract_statements(MockObject()) is None

        # Test with object that has body but it's not a list/tuple
        class MockIndentedBlock:
            def __init__(self, body):
                self.body = body

        # Test with string body (should return None)
        mock_block = MockIndentedBlock("not a list")
        assert _safe_extract_statements(mock_block) is None

        # Test with deeply nested structure (simulating pathological case)
        deep_block = MockIndentedBlock(MockIndentedBlock(MockIndentedBlock([1, 2, 3])))
        result = _safe_extract_statements(deep_block)
        assert result == [1, 2, 3]

        # Test with too deeply nested structure (should hit max_depth)
        too_deep = MockIndentedBlock(None)
        current = too_deep
        for _i in range(10):  # Create 10 levels deep
            current.body = MockIndentedBlock(None)
            current = current.body

        # This should return None due to hitting max_depth
        result = _safe_extract_statements(too_deep)
        assert result is None

    def test_cli_processing_of_complex_file(self, tmp_path):
        """Test that the CLI can process the complex nesting file without errors."""
        import subprocess
        import sys
        from pathlib import Path

        # Get the path to the complex test file
        complex_file = Path(__file__).parent.parent / "data" / "complex_nesting" / "deeply_nested_control_flow.txt"

        # Run the CLI command with dry-run to avoid file I/O issues in test
        cmd = [
            sys.executable,
            "-m",
            "splurge_unittest_to_pytest.cli",
            "migrate",
            "--dry-run",
            "--verbose",
            str(complex_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())

        # The command should succeed (exit code 0)
        assert result.returncode == 0, f"CLI failed with stderr: {result.stderr}"

        # Should see the pipeline and job completion messages
        assert "Starting migration pipeline:" in result.stdout
        assert "[SUCCESS] Migration completed successfully:" in result.stdout

        # Should contain the transformed output in dry-run mode
        assert "from unittest.mock import Mock, patch" in result.stdout
        assert "import pytest" in result.stdout
        assert "class TestDeeplyNestedControlFlow" in result.stdout
