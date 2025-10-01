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
