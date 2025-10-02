import os
import tempfile
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.events import EventBus
from splurge_unittest_to_pytest.jobs.output_job import OutputJob


def test_create_backup_creates_file(tmp_path):
    # create a temporary source file
    src = tmp_path / "source.py"
    src.write_text("print('hello')")

    # context-like object with required attributes
    class C:
        source_file = str(src)
        target_file = str(src)
        config = type("C", (), {"backup_originals": True})

    event_bus = EventBus()
    job = OutputJob(event_bus)

    # ensure no backup exists yet
    backup = Path(str(src)).with_suffix(f"{src.suffix}.backup")
    if backup.exists():
        backup.unlink()

    job._create_backup(str(src))
    assert backup.exists()


def test_create_backup_skips_if_exists(tmp_path):
    src = tmp_path / "source2.py"
    src.write_text("print('hi')")
    backup = Path(str(src)).with_suffix(f"{src.suffix}.backup")
    backup.write_text("old")

    event_bus = EventBus()
    job = OutputJob(event_bus)

    # should not raise and should not overwrite
    job._create_backup(str(src))
    assert backup.read_text() == "old"


def test_create_backup_with_custom_root(tmp_path):
    """Test that backup is created in the specified backup_root directory."""
    src = tmp_path / "source3.py"
    src.write_text("print('hello')")

    backup_root = tmp_path / "custom_backups"
    expected_backup = backup_root / src.name
    backup_path = expected_backup.with_suffix(expected_backup.suffix + ".backup")

    event_bus = EventBus()
    job = OutputJob(event_bus)

    # ensure no backup exists yet
    if backup_path.exists():
        backup_path.unlink()

    job._create_backup(str(src), str(backup_root))
    assert backup_path.exists()

    # Original location should not have a backup
    original_backup = src.with_suffix(src.suffix + ".backup")
    assert not original_backup.exists()


def test_create_backup_with_none_root(tmp_path):
    """Test that backup works with None backup_root (default behavior)."""
    src = tmp_path / "source4.py"
    src.write_text("print('test')")

    backup_path = src.with_suffix(src.suffix + ".backup")

    event_bus = EventBus()
    job = OutputJob(event_bus)

    # ensure no backup exists yet
    if backup_path.exists():
        backup_path.unlink()

    job._create_backup(str(src), None)
    assert backup_path.exists()


def test_create_backup_root_creates_directory(tmp_path):
    """Test that backup_root directory is created if it doesn't exist."""
    src = tmp_path / "source5.py"
    src.write_text("print('test')")

    backup_root = tmp_path / "new_directory" / "backups"
    expected_backup = backup_root / src.name
    backup_path = expected_backup.with_suffix(expected_backup.suffix + ".backup")

    event_bus = EventBus()
    job = OutputJob(event_bus)

    # ensure no backup exists yet and directory doesn't exist
    if backup_path.exists():
        backup_path.unlink()
    if backup_root.exists():
        import shutil

        shutil.rmtree(backup_root)

    job._create_backup(str(src), str(backup_root))
    assert backup_path.exists()
    assert backup_root.exists()
