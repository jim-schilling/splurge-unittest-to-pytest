"""Unit tests for helpers.path_utils

Covers validate_target_path (pure) and ensure_parent_dir (side-effect).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.helpers.path_utils import (
    PathValidationError,
    ensure_parent_dir,
    validate_target_path,
)


def test_validate_target_path_basic(tmp_path: Path):
    p = tmp_path / "subdir" / "file.txt"
    validated = validate_target_path(p)
    assert isinstance(validated, Path)
    assert str(validated).endswith("file.txt")


def test_ensure_parent_dir_creates(tmp_path: Path):
    p = tmp_path / "newdir" / "file.txt"
    # Ensure parent does not exist
    parent = p.parent
    assert not parent.exists()
    ensure_parent_dir(p)
    assert parent.exists() and parent.is_dir()


def test_ensure_parent_dir_permission_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    p = tmp_path / "writedir" / "file.txt"

    # Simulate permission error when mkdir is called
    def fake_mkdir(*args, **kwargs):
        raise PermissionError("no permission")

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    with pytest.raises(PathValidationError) as exc:
        ensure_parent_dir(p)
    assert "Cannot create parent directory" in str(exc.value)
