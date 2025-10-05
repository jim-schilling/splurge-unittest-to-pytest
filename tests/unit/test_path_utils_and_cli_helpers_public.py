import os
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.cli_helpers import (
    _apply_defaults_to_config,
    create_config,
    detect_test_prefixes_from_files,
    prepare_config,
)
from splurge_unittest_to_pytest.helpers.path_utils import (
    PathValidationError,
    ensure_parent_dir,
    get_path_info,
    normalize_path_for_display,
    safe_path_operation,
    suggest_path_fixes,
    validate_source_path,
    validate_target_path,
)


def test_validate_source_and_target_and_parent(tmp_path):
    p = tmp_path / "foo.py"
    p.write_text("x = 1")
    assert validate_source_path(str(p)) == p
    assert validate_target_path(str(p)) == p

    # ensure parent creation
    newdir = tmp_path / "newdir" / "file.py"
    ensure_parent_dir(newdir)
    assert (tmp_path / "newdir").exists()


def test_normalize_and_get_info(tmp_path):
    p = tmp_path / "bar.txt"
    p.write_text("ok")
    s = normalize_path_for_display(p, force_posix=True)
    assert "/" in s
    info = get_path_info(p)
    assert info["exists"] is True


def test_suggest_path_fixes_and_safe_op(tmp_path):
    missing = str(tmp_path / "missing.txt")
    s = suggest_path_fixes(FileNotFoundError("nope"), missing)
    assert any("Check if the path exists" in x or "Create the parent directory" in x for x in s)

    # safe operation should raise our PathValidationError
    def op():
        raise FileNotFoundError("nope")

    with pytest.raises(PathValidationError):
        safe_path_operation("read", missing, op)


def test_create_config_and_detect_prefixes(tmp_path):
    cfg = create_config(dry_run=True, file_patterns=["test_*.py"], test_method_prefixes=["test_"])
    assert cfg.dry_run is True

    # create a temp file with a test function
    f = tmp_path / "t.py"
    f.write_text("def test_hello():\n    pass\n")
    prefixes = detect_test_prefixes_from_files([str(f)])
    assert "test_" in prefixes[0]


def test_apply_defaults_and_prepare_config():
    base = None
    questions = [{"key": "line_length", "default": 80}]
    cfg = _apply_defaults_to_config(base, questions)
    assert cfg.line_length == 80

    # prepare_config should return a MigrationConfig
    final = prepare_config(base_config=cfg, enhanced_kwargs={})
    # Ensure it's a dataclass-like object with expected attribute
    assert hasattr(final, "line_length")
