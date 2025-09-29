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
    try:
        orch.migrate_file("this_file_does_not_exist_12345.py")
        raise AssertionError("Expected migrate_file to raise ValueError for missing source")
    except ValueError as e:
        assert "Source file does not exist" in str(e)
