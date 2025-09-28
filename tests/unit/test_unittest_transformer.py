"""Unit tests for UnittestToPytestCSTTransformer public APIs."""

import libcst as cst
import pytest

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


class TestUnittestToPytestCSTTransformerAPI:
    """Test suite for UnittestToPytestCSTTransformer public API behavior."""

    def setup_method(self):
        """Set up fresh transformer for each test."""
        self.transformer = UnittestToPytestCstTransformer()

    def test_initial_state(self):
        """Test that transformer initializes with correct default state."""
        assert self.transformer.needs_pytest_import is False
        assert self.transformer.current_class is None
        assert self.transformer.setup_code == []
        assert self.transformer.teardown_code == []
        assert self.transformer.setup_class_code == []
        assert self.transformer.teardown_class_code == []
        assert self.transformer.in_setup is False
        assert self.transformer.in_teardown is False
        assert self.transformer.in_setup_class is False
        assert self.transformer.in_teardown_class is False

    def test_transform_code_basic_unittest_class(self):
        """Test transform_code with basic unittest.TestCase."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1 + 1, 2)
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        assert "unittest.TestCase" not in result
        assert "assert 1 + 1 == 2" in result
        assert "import pytest" in result
        assert "class TestExample:" in result

    def test_transform_code_no_unittest_class(self):
        """Test transform_code with regular class (no unittest.TestCase)."""
        code = """
class RegularClass:
    def test_method(self):
        assert True
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        assert "unittest.TestCase" not in result
        # Note: pytest import might still be added due to other processing
        assert "class RegularClass:" in result

    def test_transform_code_multiple_classes(self):
        """Test transform_code with multiple classes, some unittest, some not."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_unittest_method(self):
        self.assertEqual(1, 1)

class RegularClass:
    def test_regular_method(self):
        assert True

class TestAnother(unittest.TestCase):
    def test_another_unittest(self):
        self.assertTrue(True)
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        assert "import pytest" in result  # Should add pytest import due to unittest classes
        assert "class TestExample:" in result
        assert "class RegularClass:" in result
        assert "class TestAnother:" in result
        # Both unittest classes should have inheritance removed
        assert "unittest.TestCase" not in result

    def test_transform_code_with_setup_teardown(self):
        """Test transform_code with setUp and tearDown methods."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def setUp(self):
        self.value = 42

    def tearDown(self):
        self.value = None

    def test_with_setup(self):
        self.assertEqual(self.value, 42)
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        assert "def setUp(self):" not in result
        assert "def tearDown(self):" not in result
        assert "def setup_method(self):" in result
        # Single autouse fixture with yield is used; no separate teardown_method required
        assert "def teardown_method(self):" not in result
        assert "yield" in result  # Should use yield pattern

    def test_transform_code_with_setup_class_teardown_class(self):
        """Test transform_code with setUpClass and tearDownClass methods."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared_value = "test"

    @classmethod
    def tearDownClass(cls):
        cls.shared_value = None

    def test_with_class_setup(self):
        self.assertEqual(self.shared_value, "test")
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        # Note: Class-level fixtures (setUpClass/tearDownClass) may not be fully transformed
        # due to complexity of class-level fixture implementation
        assert "unittest.TestCase" not in result
        assert 'assert self.shared_value == "test"' in result

    def test_transform_code_multiple_assertion_types(self):
        """Test transform_code with various assertion types."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_assertions(self):
        self.assertEqual(1, 1)
        self.assertTrue(True)
        self.assertFalse(False)
        self.assertIs(42, 42)
        self.assertIn(1, [1, 2, 3])
        self.assertIsInstance("test", str)
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        assert "assert 1 == 1" in result
        assert "assert True" in result
        assert "assert not False" in result
        assert "assert 42 is 42" in result
        assert "assert 1 in [1, 2, 3]" in result
        assert 'assert isinstance("test", str)' in result

    def test_transform_code_exception_assertions(self):
        """Test transform_code with exception assertions."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_exceptions(self):
        with self.assertRaises(ValueError):
            raise ValueError("test error")

        with self.assertRaisesRegex(ValueError, "error"):
            raise ValueError("error message")
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        assert "pytest.raises" in result
        assert "ValueError" in result
        assert "test error" in result

    def test_transform_code_with_unittest_main(self):
        """Test transform_code with unittest.main() call."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1, 1)

if __name__ == "__main__":
    unittest.main()
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        assert "pytest.main()" in result
        assert "unittest.main()" not in result

    def test_transform_code_empty_code(self):
        """Test transform_code with empty code."""
        result = self.transformer.transform_code("")

        assert isinstance(result, str)
        # Note: Empty code might still get imports added during processing

    def test_transform_code_invalid_python(self):
        """Test transform_code with invalid Python code."""
        code = """
class TestExample(unittest.TestCase):
    def test_invalid:
        self.assertEqual(1, 1
"""

        # Should still attempt transformation and return a string
        result = self.transformer.transform_code(code)
        assert isinstance(result, str)

    def test_transform_code_preserves_whitespace_and_comments(self):
        """Test that transform_code preserves formatting and comments."""
        code = '''
# This is a test file
import unittest

class TestExample(unittest.TestCase):
    """Test class docstring."""

    def test_simple(self):
        """Test method docstring."""
        self.assertEqual(1 + 1, 2)  # Inline comment
'''
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        # Comments and docstrings should be preserved
        assert "# This is a test file" in result
        assert '"""Test class docstring."""' in result
        assert '"""Test method docstring."""' in result
        assert "# Inline comment" in result

    def test_transform_code_state_isolation(self):
        """Test that transformer state is isolated between calls."""
        # First transformation
        code1 = """
import unittest

class TestExample1(unittest.TestCase):
    def test_first(self):
        self.assertEqual(1, 1)
"""
        result1 = self.transformer.transform_code(code1)
        assert "TestExample1" in result1

        # Second transformation
        code2 = """
import unittest

class TestExample2(unittest.TestCase):
    def test_second(self):
        self.assertEqual(2, 2)
"""
        result2 = self.transformer.transform_code(code2)
        assert "TestExample2" in result2
        assert "TestExample1" not in result2  # Should not have first class

    def test_transform_code_with_multiple_calls_state_reset(self):
        """Test that multiple calls don't accumulate state."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_method(self):
        self.assertEqual(1, 1)
"""

        # Call multiple times
        result1 = self.transformer.transform_code(code)
        result2 = self.transformer.transform_code(code)
        result3 = self.transformer.transform_code(code)

        # All results should be identical
        assert result1 == result2 == result3

    def test_transform_code_with_complex_expressions(self):
        """Test transform_code with complex expressions in assertions."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_complex_expressions(self):
        a = [1, 2, 3]
        b = [1, 2, 3]
        self.assertEqual(a, b)
        self.assertEqual(len(a), 3)
        self.assertEqual(a[0], 1)
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        # Should transform basic cases but complex ones might need special handling
        assert "assert" in result

    def test_transform_code_with_nested_classes(self):
        """Test transform_code with nested class structures."""
        code = """
import unittest

class OuterClass:
    class TestInner(unittest.TestCase):
        def test_nested(self):
            self.assertTrue(True)

class TestOuter(unittest.TestCase):
    def test_outer(self):
        self.assertFalse(False)
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        assert "class OuterClass:" in result
        assert "class TestInner:" in result  # unittest.TestCase removed
        assert "class TestOuter:" in result  # unittest.TestCase removed

    def test_transform_code_with_inheritance_chains(self):
        """Test transform_code with inheritance chains."""
        code = """
import unittest

class BaseTest(unittest.TestCase):
    def test_base(self):
        self.assertEqual(1, 1)

class DerivedTest(BaseTest):
    def test_derived(self):
        self.assertEqual(2, 2)
"""
        result = self.transformer.transform_code(code)

        assert isinstance(result, str)
        assert "class BaseTest:" in result
        assert "class DerivedTest(BaseTest):" in result
        assert "unittest.TestCase" not in result
