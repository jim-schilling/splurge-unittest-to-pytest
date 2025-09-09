"""Tests for main conversion functions."""

import tempfile
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.main import (
    convert_file,
    find_unittest_files,
    is_unittest_file,
)


class TestFileOperations:
    """Test file-based conversion operations."""

    def test_convert_file_in_place(self) -> None:
        """Test converting a file in place."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1, 1)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unittest_code)
            temp_path = Path(f.name)
        
        try:
            result = convert_file(temp_path)
            
            assert result.has_changes
            assert "assert 1 == 1" in result.converted_code
            
            # Check that file was actually modified
            converted_content = temp_path.read_text()
            assert "assert 1 == 1" in converted_content
            assert "assertEqual" not in converted_content
            
        finally:
            temp_path.unlink()

    def test_convert_file_to_different_location(self) -> None:
        """Test converting a file to a different location."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unittest_code)
            input_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            result = convert_file(input_path, output_path)
            
            assert result.has_changes
            assert "assert True" in result.converted_code
            
            # Check that output file was created with converted content
            assert output_path.exists()
            converted_content = output_path.read_text()
            assert "assert True" in converted_content
            
            # Check that input file is unchanged
            original_content = input_path.read_text()
            assert original_content == unittest_code
            
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    def test_convert_nonexistent_file(self) -> None:
        """Test handling of nonexistent input file."""
        with pytest.raises(FileNotFoundError):
            convert_file("nonexistent_file.py")

    def test_convert_file_no_changes(self) -> None:
        """Test converting a file that doesn't need changes."""
        pytest_code = """
import pytest

class TestExample:
    def test_something(self):
        assert 1 == 1
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(pytest_code)
            temp_path = Path(f.name)
        
        try:
            result = convert_file(temp_path)
            
            assert not result.has_changes
            assert result.converted_code == pytest_code
            
            # File should remain unchanged
            unchanged_content = temp_path.read_text()
            assert unchanged_content == pytest_code
            
        finally:
            temp_path.unlink()


class TestUnittestFileDetection:
    """Test detection of unittest files."""

    def test_is_unittest_file_positive_cases(self) -> None:
        """Test detection of files that contain unittest code."""
        unittest_indicators = [
            "import unittest",
            "from unittest import TestCase",
            "class TestExample(unittest.TestCase):",
            "def setUp(self):",
            "def tearDown(self):",
            "self.assertEqual(1, 1)",
            "self.assertTrue(True)",
        ]
        
        for indicator in unittest_indicators:
            code = f"""
{indicator}

def test_something():
    pass
"""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = Path(f.name)
            
            try:
                assert is_unittest_file(temp_path), f"Failed to detect unittest file with: {indicator}"
            finally:
                temp_path.unlink()

    def test_is_unittest_file_negative_cases(self) -> None:
        """Test files that should not be detected as unittest files."""
        non_unittest_codes = [
            "import pytest\n\ndef test_something():\n    assert True",
            "def some_function():\n    return 42",
            "import os\n\nprint('hello world')",
            "",  # Empty file
        ]
        
        for code in non_unittest_codes:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = Path(f.name)
            
            try:
                assert not is_unittest_file(temp_path), f"Incorrectly detected unittest file with: {code[:50]}..."
            finally:
                temp_path.unlink()

    def test_is_unittest_file_non_python_file(self) -> None:
        """Test that non-Python files are not detected as unittest files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("import unittest\nclass TestExample(unittest.TestCase): pass")
            temp_path = Path(f.name)
        
        try:
            assert not is_unittest_file(temp_path)
        finally:
            temp_path.unlink()

    def test_is_unittest_file_nonexistent(self) -> None:
        """Test that nonexistent files are not detected as unittest files."""
        assert not is_unittest_file("nonexistent_file.py")


class TestDirectoryScanning:
    """Test directory scanning for unittest files."""

    def test_find_unittest_files_in_directory(self) -> None:
        """Test finding unittest files in a directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create unittest files
            unittest_file1 = temp_path / "test_example1.py"
            unittest_file1.write_text("""
import unittest

class TestExample1(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
""")
            
            unittest_file2 = temp_path / "subdir" / "test_example2.py"
            unittest_file2.parent.mkdir()
            unittest_file2.write_text("""
from unittest import TestCase

class TestExample2(TestCase):
    def test_something(self):
        self.assertEqual(1, 1)
""")
            
            # Create non-unittest files
            pytest_file = temp_path / "test_pytest.py"
            pytest_file.write_text("""
import pytest

def test_something():
    assert True
""")
            
            regular_file = temp_path / "module.py"
            regular_file.write_text("""
def some_function():
    return 42
""")
            
            non_python_file = temp_path / "readme.txt"
            non_python_file.write_text("This is a readme file")
            
            # Find unittest files
            unittest_files = find_unittest_files(temp_path)
            
            # Should find exactly the two unittest files
            assert len(unittest_files) == 2
            found_names = {f.name for f in unittest_files}
            assert found_names == {"test_example1.py", "test_example2.py"}

    def test_find_unittest_files_empty_directory(self) -> None:
        """Test finding unittest files in an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            unittest_files = find_unittest_files(temp_path)
            assert len(unittest_files) == 0

    def test_find_unittest_files_no_unittest_files(self) -> None:
        """Test finding unittest files in a directory with no unittest files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create only non-unittest files
            pytest_file = temp_path / "test_pytest.py"
            pytest_file.write_text("import pytest\ndef test_something(): assert True")
            
            regular_file = temp_path / "module.py"
            regular_file.write_text("def some_function(): return 42")
            
            unittest_files = find_unittest_files(temp_path)
            assert len(unittest_files) == 0

    def test_find_unittest_files_nonexistent_directory(self) -> None:
        """Test finding unittest files in a nonexistent directory."""
        unittest_files = find_unittest_files("nonexistent_directory")
        assert len(unittest_files) == 0

    def test_find_unittest_files_file_not_directory(self) -> None:
        """Test finding unittest files when given a file path instead of directory."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("import unittest")
            temp_path = Path(f.name)
        
        try:
            unittest_files = find_unittest_files(temp_path)
            assert len(unittest_files) == 0
        finally:
            temp_path.unlink()


class TestEncodingHandling:
    """Test handling of different text encodings."""

    def test_convert_file_utf8_encoding(self) -> None:
        """Test converting a file with UTF-8 encoding."""
        unittest_code = """# -*- coding: utf-8 -*-
import unittest

class TestExample(unittest.TestCase):
    def test_unicode(self):
        self.assertEqual("café", "café")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(unittest_code)
            temp_path = Path(f.name)
        
        try:
            result = convert_file(temp_path, encoding='utf-8')
            
            assert result.has_changes
            assert 'assert "café" == "café"' in result.converted_code
            
        finally:
            temp_path.unlink()

    def test_convert_file_custom_encoding(self) -> None:
        """Test converting a file with a custom encoding."""
        unittest_code = """import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='latin1') as f:
            f.write(unittest_code)
            temp_path = Path(f.name)
        
        try:
            result = convert_file(temp_path, encoding='latin1')
            
            assert result.has_changes
            assert "assert True" in result.converted_code
            
        finally:
            temp_path.unlink()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_convert_file_with_syntax_error(self) -> None:
        """Test converting a file with syntax errors."""
        invalid_code = """
import unittest

class TestExample(unittest.TestCase
    def test_something(self):
        self.assertTrue(True)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(invalid_code)
            temp_path = Path(f.name)
        
        try:
            result = convert_file(temp_path)
            
            assert not result.has_changes
            assert len(result.errors) > 0
            assert "Failed to parse" in result.errors[0]
            
            # File should remain unchanged
            unchanged_content = temp_path.read_text()
            assert unchanged_content == invalid_code
            
        finally:
            temp_path.unlink()

    def test_convert_empty_file(self) -> None:
        """Test converting an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("")
            temp_path = Path(f.name)
        
        try:
            result = convert_file(temp_path)
            
            assert not result.has_changes
            assert result.converted_code == ""
            assert len(result.errors) == 0
            
        finally:
            temp_path.unlink()

    def test_convert_file_whitespace_only(self) -> None:
        """Test converting a file with only whitespace."""
        whitespace_code = "   \n\n  \t  \n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(whitespace_code)
            temp_path = Path(f.name)
        
        try:
            result = convert_file(temp_path)
            
            assert not result.has_changes
            assert result.converted_code == whitespace_code
            assert len(result.errors) == 0
            
        finally:
            temp_path.unlink()