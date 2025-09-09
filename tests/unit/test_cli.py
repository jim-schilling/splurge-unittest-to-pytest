"""Tests for the CLI interface."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from splurge_unittest_to_pytest.cli import main


class TestCLIBasicFunctionality:
    """Test basic CLI functionality."""

    def test_cli_help(self) -> None:
        """Test that the CLI help message works."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        
        assert result.exit_code == 0
        assert "Convert unittest-style tests to pytest-style tests" in result.output
        assert "--dry-run" in result.output
        assert "--recursive" in result.output

    def test_cli_version(self) -> None:
        """Test that the CLI version command works."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        
        assert result.exit_code == 0
        assert "2025.0.0" in result.output

    def test_cli_no_paths(self) -> None:
        """Test CLI behavior when no paths are provided."""
        runner = CliRunner()
        result = runner.invoke(main, [])
        
        assert result.exit_code == 1
        assert "Error: No paths provided" in result.output


class TestCLIFileConversion:
    """Test CLI file conversion functionality."""

    def test_cli_convert_single_file(self) -> None:
        """Test converting a single file via CLI."""
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
            runner = CliRunner()
            result = runner.invoke(main, [str(temp_path)])
            
            assert result.exit_code == 0
            assert f"Converted: {temp_path}" in result.output
            assert "Processed 1 files:" in result.output
            assert "1 files converted" in result.output
            
            # Check that file was actually converted
            converted_content = temp_path.read_text()
            assert "assert 1 == 1" in converted_content
            assert "assertEqual" not in converted_content
            
        finally:
            temp_path.unlink()

    def test_cli_dry_run(self) -> None:
        """Test CLI dry run functionality."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unittest_code)
            temp_path = Path(f.name)
        
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--dry-run", str(temp_path)])
            
            assert result.exit_code == 0
            assert f"Would convert: {temp_path}" in result.output
            assert "1 files would be converted" in result.output
            
            # Check that file was NOT actually modified
            unchanged_content = temp_path.read_text()
            assert unchanged_content == unittest_code
            
        finally:
            temp_path.unlink()

    def test_cli_verbose_output(self) -> None:
        """Test CLI verbose output."""
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
            runner = CliRunner()
            result = runner.invoke(main, ["--verbose", str(temp_path)])
            
            assert result.exit_code == 0
            assert f"Processing: {temp_path}" in result.output
            assert f"Converted: {temp_path}" in result.output
            
        finally:
            temp_path.unlink()

    def test_cli_output_directory(self) -> None:
        """Test CLI output directory functionality."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unittest_code)
            input_path = Path(f.name)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "converted"
            
            try:
                runner = CliRunner()
                result = runner.invoke(main, ["--output", str(output_dir), str(input_path)])
                
                assert result.exit_code == 0
                assert f"Converted: {input_path}" in result.output
                
                # Check that output file was created
                output_path = output_dir / input_path.name
                assert output_path.exists()
                
                converted_content = output_path.read_text()
                assert "assert True" in converted_content
                
                # Check that input file is unchanged
                original_content = input_path.read_text()
                assert original_content == unittest_code
                
            finally:
                input_path.unlink()


    def test_cli_backup_basic(self) -> None:
        """Test CLI backup functionality with long option."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unittest_code)
            input_path = Path(f.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"

            try:
                runner = CliRunner()
                result = runner.invoke(main, ["--backup", str(backup_dir), str(input_path)])

                assert result.exit_code == 0
                assert f"Converted: {input_path}" in result.output

                # Check that backup file was created
                backup_path = backup_dir / f"{input_path.name}.bak"
                assert backup_path.exists()

                # Check backup content matches original
                backup_content = backup_path.read_text()
                assert backup_content == unittest_code

                # Check that input file was converted
                converted_content = input_path.read_text()
                assert "assert True" in converted_content
                assert "assertEqual" not in converted_content

            finally:
                input_path.unlink()

    def test_cli_backup_short_option(self) -> None:
        """Test CLI backup functionality with short option."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1, 1)
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unittest_code)
            input_path = Path(f.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"

            try:
                runner = CliRunner()
                result = runner.invoke(main, ["-b", str(backup_dir), str(input_path)])

                assert result.exit_code == 0
                assert f"Converted: {input_path}" in result.output

                # Check that backup file was created
                backup_path = backup_dir / f"{input_path.name}.bak"
                assert backup_path.exists()

                # Check backup content matches original
                backup_content = backup_path.read_text()
                assert backup_content == unittest_code

            finally:
                input_path.unlink()

    def test_cli_backup_with_verbose(self) -> None:
        """Test CLI backup functionality with verbose output."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unittest_code)
            input_path = Path(f.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"

            try:
                runner = CliRunner()
                result = runner.invoke(main, ["--backup", str(backup_dir), "--verbose", str(input_path)])

                assert result.exit_code == 0
                assert f"Processing: {input_path}" in result.output
                assert f"Backup created: {backup_dir / input_path.name}.bak" in result.output
                assert f"Converted: {input_path}" in result.output

            finally:
                input_path.unlink()

    def test_cli_backup_with_output_directory(self) -> None:
        """Test CLI backup functionality combined with output directory."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1, 1)
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unittest_code)
            input_path = Path(f.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            backup_dir = temp_path / "backups"
            output_dir = temp_path / "output"

            try:
                runner = CliRunner()
                result = runner.invoke(main, [
                    "--backup", str(backup_dir),
                    "--output", str(output_dir),
                    str(input_path)
                ])

                assert result.exit_code == 0
                assert f"Converted: {input_path}" in result.output

                # Check that backup file was created
                backup_path = backup_dir / f"{input_path.name}.bak"
                assert backup_path.exists()

                # Check that output file was created
                output_path = output_dir / input_path.name
                assert output_path.exists()

                # Check that input file is unchanged
                original_content = input_path.read_text()
                assert original_content == unittest_code

                # Check that output file is converted
                converted_content = output_path.read_text()
                assert "assert 1 == 1" in converted_content

            finally:
                input_path.unlink()

    def test_cli_backup_dry_run_no_backup_created(self) -> None:
        """Test that backup is not created during dry run."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unittest_code)
            input_path = Path(f.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"

            try:
                runner = CliRunner()
                result = runner.invoke(main, ["--backup", str(backup_dir), "--dry-run", str(input_path)])

                assert result.exit_code == 0
                assert f"Would convert: {input_path}" in result.output

                # Check that backup directory is not created during dry run
                assert not backup_dir.exists()

                # Check that input file is unchanged
                original_content = input_path.read_text()
                assert original_content == unittest_code

            finally:
                input_path.unlink()
    """Test CLI directory handling functionality."""

    def test_cli_recursive_directory(self) -> None:
        """Test CLI recursive directory processing."""
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
import unittest

class TestExample2(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1, 1)
""")
            
            # Create non-unittest file
            pytest_file = temp_path / "test_pytest.py"
            pytest_file.write_text("""
import pytest

def test_something():
    assert True
""")
            
            runner = CliRunner()
            result = runner.invoke(main, ["--recursive", "--verbose", str(temp_path)])
            
            assert result.exit_code == 0
            assert "Found 2 unittest files" in result.output
            assert "2 files converted" in result.output

    def test_cli_directory_without_recursive(self) -> None:
        """Test CLI behavior when directory is provided without --recursive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            unittest_file = temp_path / "test_example.py"
            unittest_file.write_text("""
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
""")
            
            runner = CliRunner()
            result = runner.invoke(main, [str(temp_path)])
            
            assert result.exit_code == 0
            assert f"Warning: {temp_path} is a directory. Use --recursive to search it." in result.output
            assert "No unittest files found to convert" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_cli_nonexistent_file(self) -> None:
        """Test CLI behavior with nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(main, ["nonexistent_file.py"])
        
        assert result.exit_code != 0

    def test_cli_non_python_file(self) -> None:
        """Test CLI behavior with non-Python file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not a Python file")
            temp_path = Path(f.name)
        
        try:
            runner = CliRunner()
            result = runner.invoke(main, [str(temp_path)])
            
            assert result.exit_code == 1
            assert "Failed to parse source code" in result.output
            assert "1 files had errors" in result.output
            
        finally:
            temp_path.unlink()

    def test_cli_file_with_syntax_error(self) -> None:
        """Test CLI behavior with file containing syntax errors."""
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
            runner = CliRunner()
            result = runner.invoke(main, [str(temp_path)])
            
            assert result.exit_code == 1
            assert f"Error in {temp_path}:" in result.output
            assert "1 files had errors" in result.output
            
        finally:
            temp_path.unlink()


class TestCLIEdgeCases:
    """Test CLI edge cases."""

    def test_cli_no_unittest_files_found(self) -> None:
        """Test CLI behavior when no unittest files are found."""
        pytest_code = """
import pytest

def test_something():
    assert True
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(pytest_code)
            temp_path = Path(f.name)
        
        try:
            runner = CliRunner()
            result = runner.invoke(main, [str(temp_path)])
            
            assert result.exit_code == 0
            assert "Processed 1 files" in result.output
            assert "0 files converted" in result.output
            assert "1 files unchanged" in result.output
        finally:
            temp_path.unlink()

    def test_cli_file_no_changes_needed(self) -> None:
        """Test CLI behavior when file needs no changes."""
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
            runner = CliRunner()
            result = runner.invoke(main, ["--verbose", str(temp_path)])
            
            assert result.exit_code == 0
            assert f"No changes needed: {temp_path}" in result.output
            assert "0 files converted" in result.output
            assert "1 files unchanged" in result.output
            
        finally:
            temp_path.unlink()

    def test_cli_multiple_files_mixed_results(self) -> None:
        """Test CLI with multiple files having mixed results."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
        
        pytest_code = """
import pytest

def test_something():
    assert True
"""
        
        invalid_code = """
import unittest

class TestExample(unittest.TestCase
    def test_something(self):
        self.assertTrue(True)
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            unittest_file = temp_path / "test_unittest.py"
            unittest_file.write_text(unittest_code)
            
            pytest_file = temp_path / "test_pytest.py"
            pytest_file.write_text(pytest_code)
            
            invalid_file = temp_path / "test_invalid.py"
            invalid_file.write_text(invalid_code)
            
            runner = CliRunner()
            result = runner.invoke(main, [
                str(unittest_file),
                str(pytest_file), 
                str(invalid_file)
            ])
            
            assert result.exit_code == 1  # Due to syntax error
            assert "1 files converted" in result.output
            assert "1 files had errors" in result.output
            assert "1 files unchanged" in result.output