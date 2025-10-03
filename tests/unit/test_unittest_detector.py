"""Tests for the UnittestFileDetector."""

from pathlib import Path

import pytest

from splurge_unittest_to_pytest.detectors import UnittestFileDetector


class TestUnittestFileDetector:
    """Test the AST-based unittest file detection."""

    def test_detects_basic_unittest_file(self, tmp_path):
        """Test detection of a basic unittest file."""
        detector = UnittestFileDetector()

        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1, 1)
"""
        file_path = tmp_path / "test_file.py"
        file_path.write_text(code)

        assert detector.is_unittest_file(str(file_path)) is True

    def test_rejects_non_unittest_file(self, tmp_path):
        """Test rejection of files without unittest patterns."""
        detector = UnittestFileDetector()

        code = """
def regular_function():
    assert True
    return "not a test"
"""
        file_path = tmp_path / "test_file.py"
        file_path.write_text(code)

        assert detector.is_unittest_file(str(file_path)) is False

    def test_rejects_unittest_import_only(self, tmp_path):
        """Test rejection of files that import unittest but don't use it for testing."""
        detector = UnittestFileDetector()

        code = """
import unittest

def utility_function():
    loader = unittest.TestLoader()
    return loader

class RegularClass:
    def method(self):
        return "not a test"
"""
        file_path = tmp_path / "test_file.py"
        file_path.write_text(code)

        assert detector.is_unittest_file(str(file_path)) is False

    def test_detects_from_import_unittest(self, tmp_path):
        """Test detection with 'from unittest import TestCase' pattern."""
        detector = UnittestFileDetector()

        code = """
from unittest import TestCase

class TestExample(TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        file_path = tmp_path / "test_file.py"
        file_path.write_text(code)

        assert detector.is_unittest_file(str(file_path)) is True

    def test_detects_assertion_methods_without_inheritance(self, tmp_path):
        """Test detection of assertion methods even without explicit TestCase inheritance."""
        detector = UnittestFileDetector()

        code = """
import unittest

class MyTestClass:  # Not explicitly inheriting from TestCase
    def test_method(self):
        self.assertEqual(1, 1)  # But using unittest assertions
"""
        file_path = tmp_path / "test_file.py"
        file_path.write_text(code)

        assert detector.is_unittest_file(str(file_path)) is True

    def test_rejects_files_with_unittest_in_comments(self, tmp_path):
        """Test rejection of files that mention unittest only in comments/docstrings."""
        detector = UnittestFileDetector()

        code = '''
# This file contains unittest in comments
# import unittest - this is just a comment

"""
This docstring mentions self.assertEqual but it's not real code.
"""

def some_function():
    """This function asserts something but not unittest asserts."""
    assert True  # Regular assert
    return "not a test file"
'''
        file_path = tmp_path / "test_file.py"
        file_path.write_text(code)

        assert detector.is_unittest_file(str(file_path)) is False

    def test_raises_on_missing_file(self):
        """Test that FileNotFoundError is raised for missing files."""
        detector = UnittestFileDetector()

        with pytest.raises(FileNotFoundError):
            detector.is_unittest_file("/nonexistent/file.py")

    def test_raises_on_invalid_syntax(self, tmp_path):
        """Test that SyntaxError is raised for invalid Python syntax."""
        detector = UnittestFileDetector()

        code = "this is not valid python syntax {{{"
        file_path = tmp_path / "test_file.py"
        file_path.write_text(code)

        with pytest.raises(SyntaxError):
            detector.is_unittest_file(str(file_path))

    def test_raises_on_binary_file(self, tmp_path):
        """Test that SyntaxError is raised for binary files with null bytes."""
        detector = UnittestFileDetector()

        # Create a binary file with null bytes (ast.parse raises SyntaxError for this)
        file_path = tmp_path / "test_file.py"
        file_path.write_bytes(b"\x00\x01\x02\x03binary data\x04\x05")

        with pytest.raises(SyntaxError):
            detector.is_unittest_file(str(file_path))
