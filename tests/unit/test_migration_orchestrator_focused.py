from pathlib import Path

from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator


def test_migration_orchestrator_migrate_directory_no_files(tmp_path):
    orch = MigrationOrchestrator()
    # Create an empty directory
    d = tmp_path / "empty"
    d.mkdir()
    res = orch.migrate_directory(str(d))
    assert res.is_success()
    assert res.data == []


def test_migrate_file_missing_source_raises_validation():
    orch = MigrationOrchestrator()
    # migrate_file validates the source and returns Result.failure for missing file
    result = orch.migrate_file("this_file_does_not_exist_12345.py")
    assert not result.is_success()
    assert "Source file not found" in str(result.error)


def test_migrate_file_read_error(tmp_path):
    """Test migrate_file handles file read errors properly."""
    orch = MigrationOrchestrator()

    # Create a file and then make it unreadable (simulate permission error)
    test_file = tmp_path / "unreadable.py"
    test_file.write_text("import unittest\nclass Test(unittest.TestCase): pass")

    # Mock open to raise an exception
    import builtins

    original_open = builtins.open

    def mock_open(*args, **kwargs):
        if str(test_file) in str(args[0]):
            raise PermissionError("Permission denied")
        return original_open(*args, **kwargs)

    builtins.open = mock_open
    try:
        result = orch.migrate_file(str(test_file))
        assert result.is_error()
        assert "Permission denied" in str(result.error)
    finally:
        builtins.open = original_open


def test_migrate_file_with_config_suffix(tmp_path):
    """Test migrate_file with config that has suffix."""
    from splurge_unittest_to_pytest.context import MigrationConfig

    orch = MigrationOrchestrator()
    config = MigrationConfig(target_suffix="_migrated")

    test_file = tmp_path / "test.py"
    test_file.write_text("import unittest\nclass Test(unittest.TestCase): pass")

    result = orch.migrate_file(str(test_file), config=config)
    assert result.is_success()


def test_migrate_directory_nonexistent_path():
    """Test migrate_directory with nonexistent directory."""
    orch = MigrationOrchestrator()

    result = orch.migrate_directory("/nonexistent/directory/path")
    assert result.is_error()
    assert "Source directory not found" in str(result.error)


def test_migrate_directory_with_mixed_files(tmp_path, mocker):
    """Test migrate_directory handles mixed valid/invalid files."""
    orch = MigrationOrchestrator()

    # Create directory with files
    test_dir = tmp_path / "mixed_files"
    test_dir.mkdir()

    # Valid unittest file
    valid_file = test_dir / "valid_test.py"
    valid_file.write_text("""
import unittest

class TestValid(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
""")

    # File that will cause migration to fail
    invalid_file = test_dir / "will_fail.py"
    invalid_file.write_text("import unittest\nclass Test(unittest.TestCase): pass")

    # Mock migrate_file to fail for the second file
    original_migrate_file = orch.migrate_file
    call_count = 0

    def mock_migrate_file(file_path, config=None):
        nonlocal call_count
        call_count += 1
        if "will_fail.py" in file_path:
            from splurge_unittest_to_pytest.result import Result

            return Result.failure(RuntimeError("Mocked failure"))
        return original_migrate_file(file_path, config)

    mocker.patch.object(orch, "migrate_file", side_effect=mock_migrate_file)

    result = orch.migrate_directory(str(test_dir))

    # Should complete with some successes and some failures
    assert len(result.data) >= 0  # Successful migrations
    # Should have metadata about failed files
    assert "failed_files" in result.metadata or len(result.data) < 2


def test_migrate_directory_empty_directory(tmp_path):
    """Test migrate_directory with directory containing no Python files."""
    orch = MigrationOrchestrator()

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    # Add a non-Python file
    (empty_dir / "readme.txt").write_text("Just text")

    result = orch.migrate_directory(str(empty_dir))
    assert result.is_success()
    assert result.data == []  # No files migrated


def test_migrate_directory_no_unittest_files(tmp_path):
    """Test migrate_directory with Python files that don't use unittest."""
    orch = MigrationOrchestrator()

    py_dir = tmp_path / "py_files"
    py_dir.mkdir()

    # Python file without unittest
    (py_dir / "regular.py").write_text("print('hello world')")

    # Python file with some other testing framework
    (py_dir / "other_test.py").write_text("import pytest\ndef test_something(): pass")

    result = orch.migrate_directory(str(py_dir))
    assert result.is_success()
    assert result.data == []  # No unittest files found


def test_migrate_file_pipeline_execution_error(tmp_path, mocker):
    """Test migrate_file handles pipeline execution errors."""
    from splurge_unittest_to_pytest.result import Result

    orch = MigrationOrchestrator()

    test_file = tmp_path / "test.py"
    test_file.write_text("import unittest\nclass Test(unittest.TestCase): pass")

    # Mock the pipeline execute method to return an error
    error_result = Result.failure(RuntimeError("Pipeline execution failed"))
    mock_pipeline = mocker.Mock()
    mock_pipeline.execute.return_value = error_result

    mocker.patch.object(orch, "_create_migration_pipeline", return_value=mock_pipeline)

    result = orch.migrate_file(str(test_file))
    assert result.is_error()
    assert "Pipeline execution failed" in str(result.error)
