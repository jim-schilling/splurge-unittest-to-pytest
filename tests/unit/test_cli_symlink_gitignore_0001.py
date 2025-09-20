from pathlib import Path

import pytest

from splurge_unittest_to_pytest.main import find_unittest_files


def can_create_symlink():
    # Try to create and remove a temporary symlink to check permissions
    t = Path("tmp_symlink_check")
    target = Path("tmp_symlink_target")
    try:
        target.write_text("x")
        t.symlink_to(target)
        t.unlink()
        target.unlink()
        return True
    except Exception:
        try:
            if t.exists():
                t.unlink()
            if target.exists():
                target.unlink()
        except Exception:
            pass
        return False


@pytest.mark.skipif(not can_create_symlink(), reason="symlinks not supported in this environment")
def test_follow_symlinks_false_excludes_symlink(tmp_path):
    # create a real file and a symlink to it
    d = tmp_path / "proj"
    d.mkdir()
    real = d / "real.py"
    real.write_text("import unittest\nclass TestX(unittest.TestCase):\n    pass\n")
    link = d / "link.py"
    link.symlink_to(real)

    found_follow = find_unittest_files(d, follow_symlinks=True)
    found_no_follow = find_unittest_files(d, follow_symlinks=False)

    # With follow_symlinks True, both files should be discovered
    assert any(p.name == "real.py" for p in found_follow)
    assert any(p.name == "link.py" for p in found_follow)

    # With follow_symlinks False, the symlink should be skipped
    assert any(p.name == "real.py" for p in found_no_follow)
    assert all(p.name != "link.py" for p in found_no_follow)


def test_respect_gitignore_skips_ignored(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    # create a .gitignore that ignores ignored.py
    (d / ".gitignore").write_text("ignored.py\n")
    good = d / "good.py"
    ignored = d / "ignored.py"
    good.write_text("import unittest\nclass TestGood(unittest.TestCase):\n    pass\n")
    ignored.write_text("import unittest\nclass TestIgnored(unittest.TestCase):\n    pass\n")

    found = find_unittest_files(d, respect_gitignore=True)
    assert any(p.name == "good.py" for p in found)
    assert all(p.name != "ignored.py" for p in found)
