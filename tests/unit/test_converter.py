"""Tests for the unittest to pytest converter."""

import os
import pytest
from pathlib import Path

from splurge_unittest_to_pytest import convert_string


class TestBasicAssertions:
    """Test conversion of basic unittest assertions."""

    def test_assert_equal_conversion(self) -> None:
        """Test assertEqual conversion to assert ==."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1 + 1, 2)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 1 + 1 == 2" in result.converted_code
        assert "assertEqual" not in result.converted_code

    def test_assert_true_conversion(self) -> None:
        """Test assertTrue conversion to assert."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert True" in result.converted_code
        assert "assertTrue" not in result.converted_code

    def test_assert_false_conversion(self) -> None:
        """Test assertFalse conversion to assert not."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertFalse(False)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert not False" in result.converted_code
        assert "assertFalse" not in result.converted_code

    def test_assert_is_none_conversion(self) -> None:
        """Test assertIsNone conversion to assert ... is None."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertIsNone(None)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert None is None" in result.converted_code
        assert "assertIsNone" not in result.converted_code

    def test_assert_in_conversion(self) -> None:
        """Test assertIn conversion to assert ... in ..."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertIn(1, [1, 2, 3])
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 1 in [1, 2, 3]" in result.converted_code
        assert "assertIn" not in result.converted_code

    def test_assert_is_instance_conversion(self) -> None:
        """Test assertIsInstance conversion to assert isinstance(...)."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertIsInstance(1, int)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert isinstance(1, int)" in result.converted_code
        assert "assertIsInstance" not in result.converted_code

    def test_assert_greater_conversion(self) -> None:
        """Test assertGreater conversion to assert ... > ..."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertGreater(2, 1)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 2 > 1" in result.converted_code
        assert "assertGreater" not in result.converted_code

    def test_assert_less_equal_conversion(self) -> None:
        """Test assertLessEqual conversion to assert ... <= ..."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertLessEqual(2, 2)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 2 <= 2" in result.converted_code
        assert "assertLessEqual" not in result.converted_code

    def test_assert_not_equal_conversion(self) -> None:
        """Test assertNotEqual conversion to assert !=."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertNotEqual(1, 2)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 1 != 2" in result.converted_code
        assert "assertNotEqual" not in result.converted_code

    def test_assert_is_not_none_conversion(self) -> None:
        """Test assertIsNotNone conversion to assert ... is not None."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertIsNotNone(42)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 42 is not None" in result.converted_code
        assert "assertIsNotNone" not in result.converted_code

    def test_assert_not_in_conversion(self) -> None:
        """Test assertNotIn conversion to assert ... not in ..."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertNotIn(4, [1, 2, 3])
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 4 not in [1, 2, 3]" in result.converted_code
        assert "assertNotIn" not in result.converted_code

    def test_assert_not_is_instance_conversion(self) -> None:
        """Test assertNotIsInstance conversion to assert not isinstance(...)."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertNotIsInstance("hello", int)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert not isinstance(\"hello\", int)" in result.converted_code
        assert "assertNotIsInstance" not in result.converted_code

    def test_assert_greater_equal_conversion(self) -> None:
        """Test assertGreaterEqual conversion to assert ... >= ..."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertGreaterEqual(2, 2)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 2 >= 2" in result.converted_code
        assert "assertGreaterEqual" not in result.converted_code

    def test_assert_less_conversion(self) -> None:
        """Test assertLess conversion to assert ... < ..."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertLess(1, 2)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 1 < 2" in result.converted_code
        assert "assertLess" not in result.converted_code


class TestExceptionHandling:
    """Test conversion of exception handling assertions."""

    def test_assert_raises_conversion(self) -> None:
        """Test assertRaises conversion to pytest.raises context manager."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        with self.assertRaises(ValueError):
            raise ValueError("test")
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "with pytest.raises(ValueError):" in result.converted_code
        assert "assertRaises" not in result.converted_code

    def test_assert_raises_regex_conversion(self) -> None:
        """Test assertRaisesRegex conversion to pytest.raises with match parameter."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        with self.assertRaisesRegex(ValueError, "test"):
            raise ValueError("test message")
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert 'with pytest.raises(ValueError, match = "test"):' in result.converted_code
        assert "assertRaisesRegex" not in result.converted_code


class TestClassStructure:
    """Test conversion of class structure elements."""

    def test_unittest_testcase_removal(self) -> None:
        """Test removal of unittest.TestCase inheritance."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "class TestExample():" in result.converted_code
        assert "unittest.TestCase" not in result.converted_code

    def test_setup_method_conversion(self) -> None:
        """Test setUp method conversion to pytest fixture."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def setUp(self):
        self.value = 42
    
    def test_something(self):
        self.assertEqual(self.value, 42)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "@pytest.fixture" in result.converted_code
        assert "def setup_method(self):" in result.converted_code
        assert "setUp" not in result.converted_code

    def test_teardown_method_conversion(self) -> None:
        """Test tearDown method conversion to pytest fixture with yield."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def tearDown(self):
        pass
    
    def test_something(self):
        self.assertTrue(True)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "@pytest.fixture(autouse = True)" in result.converted_code
        assert "def teardown_method(self):" in result.converted_code
        assert "tearDown" not in result.converted_code


class TestImportHandling:
    """Test handling of import statements."""

    def test_unittest_import_removal(self) -> None:
        """Test removal of unittest imports."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "import unittest" not in result.converted_code
        assert "unittest" not in result.converted_code

    def test_pytest_import_addition(self) -> None:
        """Test addition of pytest import when needed."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        with self.assertRaises(ValueError):
            raise ValueError("test")
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "import pytest" in result.converted_code


class TestComplexScenarios:
    """Test conversion of complex test scenarios."""

    def test_complete_test_class_conversion(self) -> None:
        """Test conversion of a complete test class."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def setUp(self):
        self.value = 42
    
    def test_addition(self):
        self.assertEqual(self.value + 1, 43)
    
    def test_boolean(self):
        self.assertTrue(self.value > 0)
    
    def tearDown(self):
        self.value = None
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "import pytest" in result.converted_code
        assert "class TestExample():" in result.converted_code
        assert "@pytest.fixture" in result.converted_code
        assert "def setup_method(self):" in result.converted_code
        assert "assert self.value + 1 == 43" in result.converted_code
        assert "assert self.value > 0" in result.converted_code

    def test_no_changes_needed(self) -> None:
        """Test that pure pytest code is left unchanged."""
        pytest_code = """
import pytest

def test_example():
    assert True

@pytest.fixture
def sample_fixture():
    return 42
"""
        result = convert_string(pytest_code)
        
        assert not result.has_changes
        assert result.converted_code == pytest_code

    def test_mixed_assertions(self) -> None:
        """Test conversion of mixed assertion types."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_mixed(self):
        self.assertEqual(1, 1)
        self.assertTrue(True)
        self.assertIsNone(None)
        self.assertIn(1, [1, 2, 3])
        self.assertGreater(2, 1)
"""
        result = convert_string(unittest_code)
        
        assert result.has_changes
        assert "assert 1 == 1" in result.converted_code
        assert "assert True" in result.converted_code
        assert "assert None is None" in result.converted_code
        assert "assert 1 in [1, 2, 3]" in result.converted_code
        assert "assert 2 > 1" in result.converted_code


class TestErrorHandling:
    """Test error handling for malformed code."""

    def test_invalid_syntax(self) -> None:
        """Test handling of code with syntax errors."""
        invalid_code = """
import unittest

class TestExample(unittest.TestCase
    def test_something(self):
        self.assertTrue(True)
"""
        result = convert_string(invalid_code)
        
        assert not result.has_changes
        assert len(result.errors) > 0
        assert "Failed to parse" in result.errors[0]
        assert result.converted_code == invalid_code


class TestExampleFiles:
    """Test conversion of example unittest files to ensure they compile after conversion."""

    @pytest.mark.parametrize("filename", [f"unittest_{i:02d}.txt" for i in range(1, 26)])
    def test_conversion_compiles(self, filename: str, tmp_path: Path) -> None:
        """Test that converted code from example files compiles without syntax errors."""
        # Read the example file
        example_path = Path(__file__).parent.parent / "data" / filename
        with open(example_path, "r") as f:
            unittest_code = f.read()
        
        # Convert the code
        result = convert_string(unittest_code)
        
        # Write converted code to a temporary file
        converted_file = tmp_path / f"converted_{filename.replace('.txt', '.py')}"
        converted_file.write_text(result.converted_code)
        
        # Attempt to compile the converted code
        try:
            compile(result.converted_code, str(converted_file), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Converted code from {filename} has syntax error: {e}")
        
        # Verify unittest parts are converted
        assert "unittest.TestCase" not in result.converted_code, f"unittest.TestCase inheritance should be removed from {filename}"
        assert "self.assert" not in result.converted_code, f"self.assert should be converted in {filename}"
        
        # Verify changes were made
        assert result.has_changes, f"Expected changes for {filename}"


class TestMixedUnittestPytestFiles:
    """Test conversion of files containing both unittest and pytest code."""

    @pytest.mark.parametrize("filename", [f"unittest_pytest_{i:02d}.txt" for i in range(1, 26)])
    def test_mixed_conversion(self, filename: str, tmp_path: Path) -> None:
        """Test that unittest parts are converted while pytest parts remain unchanged."""
        # Read the example file
        example_path = Path(__file__).parent.parent / "data" / filename
        with open(example_path, "r") as f:
            mixed_code = f.read()
        
        # Convert the code
        result = convert_string(mixed_code)
        
        # Write converted code to a temporary file
        converted_file = tmp_path / f"converted_{filename.replace('.txt', '.py')}"
        converted_file.write_text(result.converted_code)
        
        # Attempt to compile the converted code
        try:
            compile(result.converted_code, str(converted_file), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Converted code from {filename} has syntax error: {e}")
        
        # Verify unittest parts are converted
        assert "unittest.TestCase" not in result.converted_code, f"unittest.TestCase inheritance should be removed from {filename}"
        assert "self.assert" not in result.converted_code, f"self.assert should be converted in {filename}"
        
        # Verify pytest parts remain unchanged
        assert "import pytest" in result.converted_code or "@pytest." in result.converted_code or "pytest." in result.converted_code or "def test_" in result.converted_code, f"pytest code should remain in {filename}"
        
        # Verify changes were made
        assert result.has_changes, f"Expected changes for mixed file {filename}"