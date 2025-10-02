import os
from pathlib import Path

import pytest

from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.context import MigrationConfig

SAMPLE_SOURCE = """import unittest


class ExampleTest(unittest.TestCase):
    def test_one(self):
        self.assertEqual(1, 1)

"""


def run_migrate_on_temp(src_path: Path, config: MigrationConfig):
    # Use the programmatic API (migrate) which delegates to the orchestrator
    result = main.migrate([str(src_path)], config=config)
    return result


def test_backup_created_by_default(tmp_path: Path):
    src = tmp_path / "test_sample.py"
    src.write_text(SAMPLE_SOURCE, encoding="utf-8")

    # Default config: backup_originals is True
    cfg = MigrationConfig(dry_run=False)

    res = run_migrate_on_temp(src, cfg)
    assert res.is_success(), f"migrate failed: {res.error}"

    backup_path = src.with_suffix(src.suffix + ".backup")
    assert backup_path.exists(), "Expected .backup file to be created by default"


def test_backup_skipped_with_skip_flag(tmp_path: Path):
    src = tmp_path / "test_sample2.py"
    src.write_text(SAMPLE_SOURCE, encoding="utf-8")

    # Disable backups via config
    cfg = MigrationConfig(dry_run=False, backup_originals=False)

    res = run_migrate_on_temp(src, cfg)
    assert res.is_success(), f"migrate failed: {res.error}"

    backup_path = src.with_suffix(src.suffix + ".backup")
    assert not backup_path.exists(), "Did not expect .backup file when backups disabled"


def test_backup_with_custom_root(tmp_path: Path):
    """Test that backups are created in the specified backup_root directory."""
    src = tmp_path / "test_sample3.py"
    src.write_text(SAMPLE_SOURCE, encoding="utf-8")

    # Specify a custom backup root directory
    backup_root = tmp_path / "backups"
    cfg = MigrationConfig(dry_run=False, backup_root=str(backup_root))

    res = run_migrate_on_temp(src, cfg)
    assert res.is_success(), f"migrate failed: {res.error}"

    # Backup should be created in the backup_root directory, not next to source
    expected_backup = backup_root / src.name
    backup_path = expected_backup.with_suffix(expected_backup.suffix + ".backup")
    assert backup_path.exists(), f"Expected backup in backup_root: {backup_path}"

    # Original location should not have a backup
    original_backup = src.with_suffix(src.suffix + ".backup")
    assert not original_backup.exists(), "Did not expect backup next to source file"


def test_backup_root_creates_directory(tmp_path: Path):
    """Test that backup_root directory is created if it doesn't exist."""
    src = tmp_path / "test_sample4.py"
    src.write_text(SAMPLE_SOURCE, encoding="utf-8")

    # Specify a backup root that doesn't exist yet
    backup_root = tmp_path / "nonexistent" / "backups"
    cfg = MigrationConfig(dry_run=False, backup_root=str(backup_root))

    res = run_migrate_on_temp(src, cfg)
    assert res.is_success(), f"migrate failed: {res.error}"

    # Backup should be created and directory should exist
    expected_backup = backup_root / src.name
    backup_path = expected_backup.with_suffix(expected_backup.suffix + ".backup")
    assert backup_path.exists(), f"Expected backup in created directory: {backup_path}"
    assert backup_root.exists(), "Backup root directory should be created"
