import os
import platform
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.helpers import path_utils


def test_validate_target_path_blank_whitespace_raises():
    # Pathlib normalizes empty string to '.', so use whitespace-only to
    # trigger the module's strip-based emptiness check.
    with pytest.raises(path_utils.PathValidationError) as exc:
        path_utils.validate_target_path("   ")

    assert "cannot be empty" in str(exc.value).lower()


def test_validate_target_path_invalid_chars_raises(tmp_path):
    bad_name = "bad<name>.txt"
    target = tmp_path / bad_name
    with pytest.raises(path_utils.PathValidationError) as exc:
        path_utils.validate_target_path(target)

    assert "invalid characters" in str(exc.value).lower()


def test_validate_target_path_long_path(tmp_path):
    # validate_target_path does not enforce platform length limits; it
    # should return a Path for long names. Windows-specific behavior is
    # handled elsewhere (e.g., when interacting with the filesystem).
    long_name = "a" * 300 + ".txt"
    target = tmp_path / "deep" / long_name

    assert path_utils.validate_target_path(target) == Path(target)


def test_ensure_parent_dir_creates_parent(tmp_path):
    target = tmp_path / "nonexistent_dir" / "file.txt"
    assert not (tmp_path / "nonexistent_dir").exists()
    path_utils.ensure_parent_dir(target)
    assert (tmp_path / "nonexistent_dir").exists()


def test_ensure_parent_dir_permission_error(monkeypatch, tmp_path):
    # Simulate PermissionError during mkdir by patching Path.mkdir
    called = {}

    original_mkdir = Path.mkdir


    def fake_mkdir(self, parents=False, exist_ok=False):
        called['raised'] = True
        raise PermissionError("simulated")


    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    target = tmp_path / "dir" / "file.txt"
    with pytest.raises(path_utils.PathValidationError) as exc:
        path_utils.ensure_parent_dir(target)

    assert "cannot create parent" in str(exc.value).lower()

    # restore (monkeypatch will undo at teardown but keep explicit)
    monkeypatch.setattr(Path, "mkdir", original_mkdir)
