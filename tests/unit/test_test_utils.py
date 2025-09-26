#!/usr/bin/env python3
"""Unit tests for test utilities."""

import pytest

from tests.test_utils import (
    _extract_imports_from_cst,
    _normalize_code_structure_cst,
    assert_class_structure,
    assert_code_structure_equals,
    assert_function_exists,
    assert_has_imports,
    assert_imports_equal,
)


class TestTestUtils:
    """Test the test utility functions."""

    def test_assert_code_structure_equals_basic(self):
        """Test basic code structure comparison."""
        actual = """
import os
import sys

def test_example():
    result = 2 + 2
    assert result == 4

class MyClass:
    def method(self):
        pass
"""

        expected = """
import sys
import os

class MyClass:
    def method(self):
        pass

def test_example():
    result = 2 + 2
    assert result == 4
"""

        # Should pass - same structure, different formatting
        assert_code_structure_equals(actual, expected)

    def test_assert_code_structure_equals_different_structure(self):
        """Test that actually different structures are detected."""
        actual = """
def test_example():
    result = 2 + 2
    assert result == 4
"""

        expected = """
class DifferentClass:
    def test_example(self):
        assert 2 + 2 == 5
"""

        with pytest.raises(AssertionError, match="Code structure mismatch"):
            assert_code_structure_equals(actual, expected)

    def test_assert_imports_equal_basic(self):
        """Test basic import comparison."""
        code = """
import os
import sys
from pathlib import Path
"""

        expected_imports = ["import os", "import sys", "from pathlib import Path"]

        assert_imports_equal(code, expected_imports)

    def test_assert_imports_equal_different_imports(self):
        """Test that different imports are detected."""
        code = """
import os
import sys
"""

        expected_imports = ["import os", "import json"]

        with pytest.raises(AssertionError, match="Import mismatch"):
            assert_imports_equal(code, expected_imports)

    def test_assert_has_imports_success(self):
        """Test that required imports are present."""
        code = """
import os
import sys
from pathlib import Path
from json import loads
"""

        required_imports = ["import os", "import sys"]

        assert_has_imports(code, required_imports)

    def test_assert_has_imports_missing(self):
        """Test that missing required imports are detected."""
        code = """
import os
import sys
"""

        required_imports = ["import os", "import json"]

        with pytest.raises(AssertionError, match="Missing required imports"):
            assert_has_imports(code, required_imports)

    def test_assert_class_structure_exists(self):
        """Test that class structure validation works."""
        code = """
class MyClass:
    def method1(self):
        pass

    def method2(self):
        pass
"""

        assert_class_structure(code, "MyClass", ["method1", "method2"])

    def test_assert_class_structure_missing_method(self):
        """Test that missing methods are detected."""
        code = """
class MyClass:
    def method1(self):
        pass
"""

        with pytest.raises(AssertionError, match="Method 'method2' not found"):
            assert_class_structure(code, "MyClass", ["method1", "method2"])

    def test_assert_class_structure_missing_class(self):
        """Test that missing classes are detected."""
        code = """
def some_function():
    pass
"""

        with pytest.raises(AssertionError, match="Class 'MyClass' not found"):
            assert_class_structure(code, "MyClass")

    def test_assert_function_exists_success(self):
        """Test that existing functions are found."""
        code = """
def my_function():
    pass

def another_function():
    pass
"""

        assert_function_exists(code, "my_function")

    def test_assert_function_exists_missing(self):
        """Test that missing functions are detected."""
        code = """
def my_function():
    pass
"""

        with pytest.raises(AssertionError, match="Function 'another_function' not found"):
            assert_function_exists(code, "another_function")

    def test_normalize_code_structure_cst(self):
        """Test CST-based code structure normalization."""
        code = """
import os

def test_example():
    result = 2 + 2
    assert result == 4
"""

        normalized = _normalize_code_structure_cst(code)

        # Should contain structural elements (sorted and normalized)
        lines = normalized.strip().split("\n")
        assert len(lines) >= 2  # Should have Import and FunctionDef
        assert any("Import" in line for line in lines)
        assert any("FunctionDef" in line for line in lines)

    def test_extract_imports_from_cst(self):
        """Test CST-based import extraction."""
        code = """
import os
import sys
from pathlib import Path
"""

        imports = _extract_imports_from_cst(__import__("libcst").parse_module(code))

        assert "import os" in imports
        assert "import sys" in imports
        assert "from pathlib import Path" in imports

    def test_complex_code_structure(self):
        """Test code structure comparison with complex code."""
        actual = """
import unittest
from typing import List

class TestExample(unittest.TestCase):
    def setUp(self):
        self.value = 42

    def test_something(self):
        result = self.value + 8
        self.assertEqual(result, 50)
        self.assertTrue(result > 0)

    def test_another(self):
        data = [1, 2, 3]
        self.assertIn(2, data)
"""

        expected = """
from typing import List
import unittest

class TestExample(unittest.TestCase):
    def test_another(self):
        data = [1, 2, 3]
        self.assertIn(2, data)

    def test_something(self):
        result = 42 + 8
        self.assertEqual(result, 50)
        self.assertTrue(result > 0)

    def setUp(self):
        self.value = 42
"""

        # Should pass despite different formatting and ordering
        # Our new implementation allows for different statement ordering
        assert_code_structure_equals(actual, expected)
