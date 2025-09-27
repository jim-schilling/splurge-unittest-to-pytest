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
