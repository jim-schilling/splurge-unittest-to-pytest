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
