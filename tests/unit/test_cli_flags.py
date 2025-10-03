import os
from pathlib import Path

import pytest

from splurge_unittest_to_pytest import cli
from splurge_unittest_to_pytest import main as main_module


def write_sample(file_path: Path) -> None:
    file_path.write_text("""import unittest

class TestX(unittest.TestCase):
    def test_one(self):
        self.assertEqual(1, 1)
""")


def test_suffix_and_ext_applied(tmp_path: Path):
    src = tmp_path / "sample.py"
    write_sample(src)

    out_dir = tmp_path / "out"
    config = cli.create_config(target_root=str(out_dir), suffix="_migrated", ext="txt")

    res = main_module.migrate([str(src)], config=config)
    assert res.is_success()
    # Expect the returned path is the written target path
    assert len(res.data) == 1
    written = Path(res.data[0])
    assert written.parent == out_dir
    assert written.name == "sample_migrated.txt"
    # file should exist
    assert written.exists()


def test_suffix_sanitization(tmp_path: Path):
    src = tmp_path / "odd.name.test.py"
    write_sample(src)

    out_dir = tmp_path / "out2"
    # Provide a nasty suffix with dots and unsafe chars
    config = cli.create_config(target_root=str(out_dir), suffix="..weird..$$$..", ext=None)

    res = main_module.migrate([str(src)], config=config)
    assert res.is_success()
    written = Path(res.data[0])
    # sanitized suffix becomes '_weird' so filename should be 'odd.name.test_weird.py'
    assert written.name == "odd.name.test_weird.py"


def test_ext_normalization_and_invalid(tmp_path: Path):
    src = tmp_path / "caps.PY"
    write_sample(src)

    out_dir = tmp_path / "out3"
    # Provide uppercase ext; expect normalization to lower-case
    config = cli.create_config(target_root=str(out_dir), suffix="", ext=".TxT")

    res = main_module.migrate([str(src)], config=config)
    assert res.is_success()
    written = Path(res.data[0])
    assert written.suffix == ".txt"

    # Provide invalid extension -> should be ignored (preserve original)
    config2 = cli.create_config(target_root=str(out_dir), suffix="", ext="...!!")
    res2 = main_module.migrate([str(src)], config=config2)
    assert res2.is_success()
    written2 = Path(res2.data[0])
    assert written2.suffix == ".PY"


def test_suffix_leading_chars(tmp_path: Path):
    src = tmp_path / "base.py"
    write_sample(src)
    out_dir = tmp_path / "out4"
    # Suffix with leading underscore/hyphen should be normalized to single leading underscore
    config = cli.create_config(target_root=str(out_dir), suffix="__pref--", ext=None)
    res = main_module.migrate([str(src)], config=config)
    assert res.is_success()
    written = Path(res.data[0])
    assert written.name == "base_pref.py"


def test_dry_run_returns_path_without_writing(tmp_path: Path):
    src = tmp_path / "dry.py"
    write_sample(src)
    out_dir = tmp_path / "out_dry"
    config = cli.create_config(target_root=str(out_dir), suffix="_x", ext=None)
    config = config.with_override(dry_run=True)

    res = main_module.migrate([str(src)], config=config)
    assert res.is_success()
    written = Path(res.data[0])
    # file should NOT exist because of dry-run
    assert not written.exists()
