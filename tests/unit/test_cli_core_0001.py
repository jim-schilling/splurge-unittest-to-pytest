"""Tests for the CLI interface."""

from pathlib import Path
from typing import Any

from click.testing import CliRunner

from splurge_unittest_to_pytest.cli import main
from splurge_unittest_to_pytest import __version__

DOMAINS = ["cli", "core"]


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
        assert __version__ in result.output

    def test_cli_no_paths(self) -> None:
        """Test CLI behavior when no paths are provided."""
        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code == 1
        assert "Error: No paths provided" in result.output


class TestCLIFileConversion:
    """Test CLI file conversion functionality."""

    def test_cli_convert_single_file(self, tmp_path: Path) -> None:
        """Test converting a single file via CLI."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertEqual(1, 1)
"""

        temp_file = tmp_path / "test_single.py"
        temp_file.write_text(unittest_code)

        runner = CliRunner()
        result = runner.invoke(main, [str(temp_file)])

        assert result.exit_code == 0
        assert f"Converted: {temp_file}" in result.output
        assert "Processed 1 files:" in result.output
        assert "1 files converted" in result.output

        # Check that file was actually converted
        converted_content = temp_file.read_text()
        assert "assert 1 == 1" in converted_content
        assert "assertEqual" not in converted_content

    def test_cli_dry_run(self, tmp_path: Path) -> None:
        """Test CLI dry run functionality."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        temp_file = tmp_path / "test_dry_run.py"
        temp_file.write_text(unittest_code)

        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", str(temp_file)])

        assert result.exit_code == 0
        assert f"Would convert: {temp_file}" in result.output
        assert "1 files would be converted" in result.output

        # Check that file was NOT actually modified
        unchanged_content = temp_file.read_text()
        assert unchanged_content == unittest_code

    def test_cli_verbose_output(self, tmp_path: Path) -> None:
        """Test CLI verbose output."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertEqual(1, 1)
"""

        temp_file = tmp_path / "test_verbose.py"
        temp_file.write_text(unittest_code)

        runner = CliRunner()
        result = runner.invoke(main, ["--verbose", str(temp_file)])

        assert result.exit_code == 0
        assert f"Processing: {temp_file}" in result.output
        assert f"Converted: {temp_file}" in result.output

    def test_cli_output_directory(self, tmp_path: Path) -> None:
        """Test CLI output directory functionality."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        input_file = tmp_path / "test_input.py"
        input_file.write_text(unittest_code)

        output_dir = tmp_path / "converted"

        runner = CliRunner()
        result = runner.invoke(main, ["--output", str(output_dir), str(input_file)])

        assert result.exit_code == 0
        assert f"Converted: {input_file}" in result.output

        # Check that output file was created
        output_path = output_dir / input_file.name
        assert output_path.exists()

        converted_content = output_path.read_text()
        assert "assert True" in converted_content

        # Check that input file is unchanged
        original_content = input_file.read_text()
        assert original_content == unittest_code

    def test_cli_backup_basic(self, tmp_path: Path) -> None:
        """Test CLI backup functionality with long option."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        input_file = tmp_path / "test_backup.py"
        input_file.write_text(unittest_code)

        backup_dir = tmp_path / "backups"

        runner = CliRunner()
        result = runner.invoke(main, ["--backup", str(backup_dir), str(input_file)])

        assert result.exit_code == 0
        assert f"Converted: {input_file}" in result.output

        # Check that backup file was created
        backup_path = backup_dir / f"{input_file.name}.bak"
        assert backup_path.exists()

        # Check backup content matches original
        backup_content = backup_path.read_text()
        assert backup_content == unittest_code

        # Check that input file was converted
        converted_content = input_file.read_text()
        assert "assert True" in converted_content
        assert "assertEqual" not in converted_content

    def test_cli_backup_short_option(self, tmp_path: Path) -> None:
        """Test CLI backup functionality with short option."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertEqual(1, 1)
"""

        input_file = tmp_path / "test_backup_short.py"
        input_file.write_text(unittest_code)

        backup_dir = tmp_path / "backups"

        runner = CliRunner()
        result = runner.invoke(main, ["-b", str(backup_dir), str(input_file)])

        assert result.exit_code == 0
        assert f"Converted: {input_file}" in result.output

        # Check that backup file was created
        backup_path = backup_dir / f"{input_file.name}.bak"
        assert backup_path.exists()

        # Check backup content matches original
        backup_content = backup_path.read_text()
        assert backup_content == unittest_code

    def test_cli_backup_with_verbose(self, tmp_path: Path) -> None:
        """Test CLI backup functionality with verbose output."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        input_file = tmp_path / "test_backup_verbose.py"
        input_file.write_text(unittest_code)

        backup_dir = tmp_path / "backups"

        runner = CliRunner()
        result = runner.invoke(main, ["--backup", str(backup_dir), "--verbose", str(input_file)])

        assert result.exit_code == 0
        assert f"Processing: {input_file}" in result.output
        assert f"Backup created: {backup_dir / input_file.name}.bak" in result.output
        assert f"Converted: {input_file}" in result.output

    def test_cli_backup_with_output_directory(self, tmp_path: Path) -> None:
        """Test CLI backup functionality combined with output directory."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertEqual(1, 1)
"""

        input_file = tmp_path / "test_backup_output.py"
        input_file.write_text(unittest_code)

        backup_dir = tmp_path / "backups"
        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(main, ["--backup", str(backup_dir), "--output", str(output_dir), str(input_file)])

        assert result.exit_code == 0
        assert f"Converted: {input_file}" in result.output

        # Check that backup file was created
        backup_path = backup_dir / f"{input_file.name}.bak"
        assert backup_path.exists()

        # Check that output file was created
        output_path = output_dir / input_file.name
        assert output_path.exists()

        # Check that input file is unchanged
        original_content = input_file.read_text()
        assert original_content == unittest_code

        # Check that output file is converted
        converted_content = output_path.read_text()
        assert "assert 1 == 1" in converted_content

    def test_cli_backup_dry_run_no_backup_created(self, tmp_path: Path) -> None:
        """Test that backup is not created during dry run."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        input_file = tmp_path / "test_backup_dry_run.py"
        input_file.write_text(unittest_code)

        backup_dir = tmp_path / "backups"

        runner = CliRunner()
        result = runner.invoke(main, ["--backup", str(backup_dir), "--dry-run", str(input_file)])

        assert result.exit_code == 0
        assert f"Would convert: {input_file}" in result.output

        # Check that backup directory is not created during dry run
        assert not backup_dir.exists()

        # Check that input file is unchanged
        original_content = input_file.read_text()
        assert original_content == unittest_code

    """Test CLI directory handling functionality."""

    def test_cli_recursive_directory(self, tmp_path: Path) -> None:
        """Test CLI recursive directory processing."""
        # Create unittest files
        unittest_file1 = tmp_path / "test_example1.py"
        unittest_file1.write_text("""
import unittest

class TestExample1(unittest.TestCase):
    def test_something(self) -> None:
        self.assertTrue(True)
""")

        unittest_file2 = tmp_path / "subdir" / "test_example2.py"
        unittest_file2.parent.mkdir()
        unittest_file2.write_text("""
import unittest

class TestExample2(unittest.TestCase):
    def test_something(self) -> None:
        self.assertEqual(1, 1)
""")

        # Create non-unittest file
        pytest_file = tmp_path / "test_pytest.py"
        pytest_file.write_text("""
import pytest

def test_something():
    assert True
""")

        runner = CliRunner()
        result = runner.invoke(main, ["--recursive", "--verbose", str(tmp_path)])

        assert result.exit_code == 0
        assert "Found 2 unittest files" in result.output
        assert "2 files converted" in result.output

    def test_cli_directory_without_recursive(self, tmp_path: Path) -> None:
        """Test CLI behavior when directory is provided without --recursive."""
        unittest_file = tmp_path / "test_example.py"
        unittest_file.write_text("""
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertTrue(True)
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path)])

        assert result.exit_code == 0
        assert f"Warning: {tmp_path} is a directory. Use --recursive to search it." in result.output
        assert "No unittest files found to convert" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_cli_nonexistent_file(self) -> None:
        """Test CLI behavior with nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(main, ["nonexistent_file.py"])

        assert result.exit_code != 0

    def test_cli_non_python_file(self, tmp_path: Path) -> None:
        """Test CLI behavior with non-Python file."""
        temp_file = tmp_path / "test_non_python.txt"
        temp_file.write_text("This is not a Python file")

        runner = CliRunner()
        result = runner.invoke(main, [str(temp_file)])

        assert result.exit_code == 1
        assert "Failed to parse source code" in result.output
        assert "1 files had errors" in result.output

    def test_cli_file_with_syntax_error(self, tmp_path: Path) -> None:
        """Test CLI behavior with file containing syntax errors."""
        invalid_code = """
import unittest

class TestExample(unittest.TestCase
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        temp_file = tmp_path / "test_syntax_error.py"
        temp_file.write_text(invalid_code)

        runner = CliRunner()
        result = runner.invoke(main, [str(temp_file)])

        assert result.exit_code == 1
        assert f"Error in {temp_file}:" in result.output
        assert "1 files had errors" in result.output


class TestCLIEdgeCases:
    """Test CLI edge cases."""

    def test_cli_no_unittest_files_found(self, tmp_path: Path) -> None:
        """Test CLI behavior when no unittest files are found."""
        pytest_code = """
import pytest

def test_something():
    assert True
"""

        temp_file = tmp_path / "test_pytest.py"
        temp_file.write_text(pytest_code)

        runner = CliRunner()
        result = runner.invoke(main, [str(temp_file)])

        assert result.exit_code == 0
        assert "Processed 1 files" in result.output
        assert "0 files converted" in result.output
        assert "1 files unchanged" in result.output

    def test_cli_file_no_changes_needed(self, tmp_path: Path) -> None:
        """Test CLI behavior when file needs no changes."""
        pytest_code = """
import pytest

class TestExample:
    def test_something(self) -> None:
        assert 1 == 1
"""

        temp_file = tmp_path / "test_no_changes.py"
        temp_file.write_text(pytest_code)

        runner = CliRunner()
        result = runner.invoke(main, ["--verbose", str(temp_file)])

        assert result.exit_code == 0
        assert f"No changes needed: {temp_file}" in result.output
        assert "0 files converted" in result.output
        assert "1 files unchanged" in result.output

    def test_cli_multiple_files_mixed_results(self, tmp_path: Path) -> None:
        """Test CLI with multiple files having mixed results."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
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
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        unittest_file = tmp_path / "test_unittest.py"
        unittest_file.write_text(unittest_code)

        pytest_file = tmp_path / "test_pytest.py"
        pytest_file.write_text(pytest_code)

        invalid_file = tmp_path / "test_invalid.py"
        invalid_file.write_text(invalid_code)

        runner = CliRunner()
        result = runner.invoke(main, [str(unittest_file), str(pytest_file), str(invalid_file)])

        assert result.exit_code == 1  # Due to syntax error
        assert "1 files converted" in result.output
        assert "1 files had errors" in result.output
        assert "1 files unchanged" in result.output

    def test_cli_dry_run_verbose_with_changes(self, tmp_path: Path) -> None:
        """Test CLI dry run with verbose output showing changes."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        temp_file = tmp_path / "test_dry_run_verbose.py"
        temp_file.write_text(unittest_code)

        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", "--verbose", str(temp_file)])

        assert result.exit_code == 0
        assert f"Would convert: {temp_file}" in result.output
        assert "Changes would be made:" in result.output
        assert "1 files would be converted" in result.output

        # Check that file was NOT actually modified
        unchanged_content = temp_file.read_text()
        assert unchanged_content == unittest_code

    def test_cli_dry_run_verbose_no_changes(self, tmp_path: Path) -> None:
        """Test CLI dry run with verbose output when no changes needed."""
        pytest_code = """
import pytest

class TestExample:
    def test_something(self) -> None:
        assert True
"""

        temp_file = tmp_path / "test_dry_run_no_changes.py"
        temp_file.write_text(pytest_code)

        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", "--verbose", str(temp_file)])

        assert result.exit_code == 0
        assert f"No changes needed: {temp_file}" in result.output
        assert "0 files would be converted" in result.output
        assert "1 files unchanged" in result.output

    def test_cli_dry_run_with_errors(self, tmp_path: Path) -> None:
        """Test CLI dry run with file containing errors."""
        invalid_code = """
import unittest

class TestExample(unittest.TestCase
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        temp_file = tmp_path / "test_dry_run_errors.py"
        temp_file.write_text(invalid_code)

        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", str(temp_file)])

        assert result.exit_code == 1
        assert f"Error in {temp_file}:" in result.output
        assert "1 files had errors" in result.output

    def test_cli_backup_creation_failure(self, tmp_path: Path, mocker: Any) -> None:
        """Test CLI behavior when backup creation fails."""
        unittest_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self) -> None:
        self.assertTrue(True)
"""

        input_file = tmp_path / "test_backup_failure.py"
        input_file.write_text(unittest_code)

        backup_dir = tmp_path / "backups"

        # Mock shutil.copy2 to raise an exception
        mocker.patch("shutil.copy2", side_effect=Exception("Mock backup failure"))
        runner = CliRunner()
        result = runner.invoke(main, ["--backup", str(backup_dir), str(input_file)])

        # Should still succeed but with warning
        assert result.exit_code == 0
        assert "Warning: Failed to create backup" in result.output
        assert f"Converted: {input_file}" in result.output

    def test_cli_encoding_error(self, tmp_path: Path) -> None:
        """Test CLI behavior with encoding errors."""
        # Create a file with invalid UTF-8 encoding
        temp_file = tmp_path / "test_encoding_error.py"
        # Write some invalid UTF-8 bytes
        temp_file.write_bytes(b"\xff\xfe\x00\x00import unittest\n")

        runner = CliRunner()
        result = runner.invoke(main, [str(temp_file)])

        assert result.exit_code == 1
        assert "Encoding error" in result.output or "Failed to decode" in result.output
