"""Tests for main conversion functions."""

from pathlib import Path

import pytest

from splurge_unittest_to_pytest.main import (
    convert_file,
    find_unittest_files,
    is_unittest_file,
)


class TestFileOperations:
    """Test file-based conversion operations."""

    def test_convert_file_in_place(self, tmp_path) -> None:
        """Test converting a file in place."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1, 1)
"""
        
        temp_path = tmp_path / "test_file.py"
        temp_path.write_text(unittest_code)
        
        result = convert_file(temp_path)
        
        assert result.has_changes
        assert "assert 1 == 1" in result.converted_code
        
        # Check that file was actually modified
        converted_content = temp_path.read_text()
        assert "assert 1 == 1" in converted_content
        assert "assertEqual" not in converted_content

    def test_convert_file_to_different_location(self, tmp_path) -> None:
        """Test converting a file to a different location."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        
        input_path = tmp_path / "input_file.py"
        output_path = tmp_path / "output_file.py"
        
        input_path.write_text(unittest_code)
        
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

    def test_convert_nonexistent_file(self) -> None:
        """Test handling of nonexistent input file."""
        from splurge_unittest_to_pytest.exceptions import FileNotFoundError
        with pytest.raises(FileNotFoundError):
            convert_file("nonexistent_file.py")

    def test_convert_file_no_changes(self, tmp_path) -> None:
        """Test converting a file that doesn't need changes."""
        pytest_code = """
import pytest

class TestExample:
    def test_something(self):
        assert 1 == 1
"""
        
        temp_path = tmp_path / "test_file.py"
        temp_path.write_text(pytest_code)
        
        result = convert_file(temp_path)
        
        assert not result.has_changes
        assert result.converted_code == pytest_code
        
        # File should remain unchanged
        unchanged_content = temp_path.read_text()
        assert unchanged_content == pytest_code


class TestUnittestFileDetection:
    """Test detection of unittest files."""

    def test_is_unittest_file_positive_cases(self, tmp_path: Path) -> None:
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
        
        for i, indicator in enumerate(unittest_indicators):
            code = f"""
{indicator}

def test_something():
    pass
"""
            temp_file = tmp_path / f"test_unittest_{i}.py"
            temp_file.write_text(code)
            
            assert is_unittest_file(temp_file), f"Failed to detect unittest file with: {indicator}"

    def test_is_unittest_file_negative_cases(self, tmp_path: Path) -> None:
        """Test files that should not be detected as unittest files."""
        non_unittest_codes = [
            "import pytest\n\ndef test_something():\n    assert True",
            "def some_function():\n    return 42",
            "import os\n\nprint('hello world')",
            "",  # Empty file
        ]
        
        for i, code in enumerate(non_unittest_codes):
            temp_file = tmp_path / f"test_non_unittest_{i}.py"
            temp_file.write_text(code)
            
            assert not is_unittest_file(temp_file), f"Incorrectly detected unittest file with: {code[:50]}..."

    def test_is_unittest_file_non_python_file(self, tmp_path: Path) -> None:
        """Test that files with unittest content are detected regardless of extension."""
        temp_file = tmp_path / "test_unittest.txt"
        temp_file.write_text("import unittest\nclass TestExample(unittest.TestCase): pass")
        
        assert is_unittest_file(temp_file)

    def test_is_unittest_file_nonexistent(self) -> None:
        """Test that nonexistent files raise FileNotFoundError."""
        from splurge_unittest_to_pytest.exceptions import FileNotFoundError
        with pytest.raises(FileNotFoundError):
            is_unittest_file("nonexistent_file.py")

    def test_convert_file_permission_error_reading(self, tmp_path: Path, mocker) -> None:
        """Test handling of permission errors when reading files."""
        # Create a temporary file and mock the read_text method to raise PermissionError
        temp_file = tmp_path / "test_permission.py"
        temp_file.write_text("import unittest\nclass Test(unittest.TestCase): pass")

        # Mock Path.read_text to raise PermissionError
        mocker.patch.object(Path, 'read_text', side_effect=PermissionError("Permission denied"))
        from splurge_unittest_to_pytest.exceptions import PermissionDeniedError
        with pytest.raises(PermissionDeniedError):
            convert_file(temp_file)

    def test_convert_file_encoding_error(self, tmp_path: Path) -> None:
        """Test handling of encoding errors when reading files."""
        # Create a file with invalid UTF-8 encoding
        temp_file = tmp_path / "test_encoding.py"
        # Write some invalid UTF-8 bytes
        temp_file.write_bytes(b'\xff\xfe\x00\x00import unittest\n')
        
        from splurge_unittest_to_pytest.exceptions import EncodingError
        with pytest.raises(EncodingError):
            convert_file(temp_file)

    def test_is_unittest_file_permission_error(self, tmp_path: Path, mocker) -> None:
        """Test handling of permission errors in is_unittest_file."""
        # Create a temporary file and mock the read_text method to raise PermissionError
        temp_file = tmp_path / "test_permission.py"
        temp_file.write_text("import unittest\nclass Test(unittest.TestCase): pass")

        # Mock Path.read_text to raise PermissionError
        mocker.patch.object(Path, 'read_text', side_effect=PermissionError("Permission denied"))
        from splurge_unittest_to_pytest.exceptions import PermissionDeniedError
        with pytest.raises(PermissionDeniedError):
            is_unittest_file(temp_file)

    def test_is_unittest_file_encoding_error(self, tmp_path: Path) -> None:
        """Test handling of encoding errors in is_unittest_file."""
        # Create a file with invalid UTF-8 encoding
        temp_file = tmp_path / "test_encoding.py"
        # Write some invalid UTF-8 bytes
        temp_file.write_bytes(b'\xff\xfe\x00\x00import unittest\n')
        
        from splurge_unittest_to_pytest.exceptions import EncodingError
        with pytest.raises(EncodingError):
            is_unittest_file(temp_file)


class TestDirectoryScanning:
    """Test directory scanning for unittest files."""

    def test_find_unittest_files_in_directory(self, tmp_path: Path) -> None:
        """Test finding unittest files in a directory structure."""
        # Create unittest files
        unittest_file1 = tmp_path / "test_example1.py"
        unittest_file1.write_text("""
import unittest

class TestExample1(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
""")
        
        unittest_file2 = tmp_path / "subdir" / "test_example2.py"
        unittest_file2.parent.mkdir()
        unittest_file2.write_text("""
from unittest import TestCase

class TestExample2(TestCase):
    def test_something(self):
        self.assertEqual(1, 1)
""")
        
        # Create non-unittest files
        pytest_file = tmp_path / "test_pytest.py"
        pytest_file.write_text("""
import pytest

def test_something():
    assert True
""")
        
        regular_file = tmp_path / "module.py"
        regular_file.write_text("""
def some_function():
    return 42
""")
        
        non_python_file = tmp_path / "readme.txt"
        non_python_file.write_text("This is a readme file")
        
        # Find unittest files
        unittest_files = find_unittest_files(tmp_path)
        
        # Should find exactly the two unittest files
        assert len(unittest_files) == 2
        found_names = {f.name for f in unittest_files}
        assert found_names == {"test_example1.py", "test_example2.py"}

    def test_find_unittest_files_empty_directory(self, tmp_path: Path) -> None:
        """Test finding unittest files in an empty directory."""
        unittest_files = find_unittest_files(tmp_path)
        assert len(unittest_files) == 0

    def test_find_unittest_files_no_unittest_files(self, tmp_path: Path) -> None:
        """Test finding unittest files in a directory with no unittest files."""
        # Create only non-unittest files
        pytest_file = tmp_path / "test_pytest.py"
        pytest_file.write_text("import pytest\ndef test_something(): assert True")
        
        regular_file = tmp_path / "module.py"
        regular_file.write_text("def some_function(): return 42")
        
        unittest_files = find_unittest_files(tmp_path)
        assert len(unittest_files) == 0

    def test_find_unittest_files_nonexistent_directory(self) -> None:
        """Test finding unittest files in a nonexistent directory."""
        unittest_files = find_unittest_files("nonexistent_directory")
        assert len(unittest_files) == 0

    def test_find_unittest_files_file_not_directory(self, tmp_path: Path) -> None:
        """Test finding unittest files when given a file path instead of directory."""
        temp_file = tmp_path / "test_file.py"
        temp_file.write_text("import unittest")
        
        unittest_files = find_unittest_files(temp_file)
        assert len(unittest_files) == 0


class TestEncodingHandling:
    """Test handling of different text encodings."""

    def test_convert_file_utf8_encoding(self, tmp_path: Path) -> None:
        """Test converting a file with UTF-8 encoding."""
        unittest_code = """# -*- coding: utf-8 -*-
import unittest

class TestExample(unittest.TestCase):
    def test_unicode(self):
        self.assertEqual("café", "café")
"""
        
        temp_file = tmp_path / "test_utf8.py"
        temp_file.write_text(unittest_code, encoding='utf-8')
        
        result = convert_file(temp_file, encoding='utf-8')
        
        assert result.has_changes
        assert 'assert "café" == "café"' in result.converted_code

    def test_convert_file_custom_encoding(self, tmp_path: Path) -> None:
        """Test converting a file with a custom encoding."""
        unittest_code = """import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        
        temp_file = tmp_path / "test_latin1.py"
        temp_file.write_text(unittest_code, encoding='latin1')
        
        result = convert_file(temp_file, encoding='latin1')
        
        assert result.has_changes
        assert "assert True" in result.converted_code


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_convert_file_with_syntax_error(self, tmp_path: Path) -> None:
        """Test converting a file with syntax errors."""
        invalid_code = """
import unittest

class TestExample(unittest.TestCase
    def test_something(self):
        self.assertTrue(True)
"""
        
        temp_file = tmp_path / "test_syntax_error.py"
        temp_file.write_text(invalid_code)
        
        result = convert_file(temp_file)
        
        assert not result.has_changes
        assert len(result.errors) > 0
        assert "Failed to parse" in result.errors[0]
        
        # File should remain unchanged
        unchanged_content = temp_file.read_text()
        assert unchanged_content == invalid_code

    def test_convert_empty_file(self, tmp_path: Path) -> None:
        """Test converting an empty file."""
        temp_file = tmp_path / "test_empty.py"
        temp_file.write_text("")
        
        result = convert_file(temp_file)
        
        assert not result.has_changes
        assert result.converted_code == ""
        assert len(result.errors) == 0

    def test_convert_file_whitespace_only(self, tmp_path: Path) -> None:
        """Test converting a file with only whitespace."""
        whitespace_code = "   \n\n  \t  \n"
        
        temp_file = tmp_path / "test_whitespace.py"
        temp_file.write_text(whitespace_code)
        
        result = convert_file(temp_file)
        
        assert not result.has_changes
        assert result.converted_code == whitespace_code
        assert len(result.errors) == 0