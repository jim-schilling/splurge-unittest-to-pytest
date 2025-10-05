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
    config = cli.create_config(target_root=str(out_dir), target_suffix="_migrated", target_extension="txt")

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
    config = cli.create_config(target_root=str(out_dir), target_suffix="..weird..$$$..", target_extension=None)

    res = main_module.migrate([str(src)], config=config)
    assert res.is_success()
    written = Path(res.data[0])
    # suffix is used as-is, so filename should be 'odd.name.test..weird..$$$...py'
    assert written.name == "odd.name.test..weird..$$$...py"


def test_ext_normalization_and_invalid(tmp_path: Path):
    src = tmp_path / "caps.PY"
    write_sample(src)

    out_dir = tmp_path / "out3"
    # Provide uppercase ext; expect normalization to lower-case
    config = cli.create_config(target_root=str(out_dir), target_suffix="", target_extension=".TxT")

    res = main_module.migrate([str(src)], config=config)
    assert res.is_success()
    written = Path(res.data[0])
    assert written.suffix == ".TxT"

    # Provide extension with dots/special chars -> used as-is
    config2 = cli.create_config(target_root=str(out_dir), target_suffix="", target_extension="...!!")
    res2 = main_module.migrate([str(src)], config=config2)
    assert res2.is_success()
    written2 = Path(res2.data[0])
    assert written2.suffix == ".!!"


def test_suffix_leading_chars(tmp_path: Path):
    src = tmp_path / "base.py"
    write_sample(src)
    out_dir = tmp_path / "out4"
    # Suffix is used as-is, no normalization of leading characters
    config = cli.create_config(target_root=str(out_dir), target_suffix="__pref--", target_extension=None)
    res = main_module.migrate([str(src)], config=config)
    assert res.is_success()
    written = Path(res.data[0])
    assert written.name == "base__pref--.py"


def test_dry_run_returns_path_without_writing(tmp_path: Path):
    src = tmp_path / "dry.py"
    write_sample(src)
    out_dir = tmp_path / "out_dry"
    config = cli.create_config(target_root=str(out_dir), target_suffix="_x", target_extension=None)
    config = config.with_override(dry_run=True)

    res = main_module.migrate([str(src)], config=config)
    assert res.is_success()
    written = Path(res.data[0])
    # file should NOT exist because of dry-run
    assert not written.exists()
