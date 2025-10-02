import tempfile
from pathlib import Path

from splurge_unittest_to_pytest import cli


def test_create_config_defaults():
    cfg = cli.create_config()
    # basic sanity checks on returned MigrationConfig
    assert cfg is not None
    assert hasattr(cfg, "target_directory")
    assert cfg.enable_decision_analysis is True


def test_validate_source_files_with_patterns(tmp_path: Path):
    # create a temp structure with a couple of .py files
    d = tmp_path / "pkg"
    d.mkdir()
    (d / "a.py").write_text("x=1\n")
    (d / "b.txt").write_text("nope\n")

    res = cli.validate_source_files_with_patterns([], str(d), ["*.py"], recurse=False)
    assert any(p.endswith("a.py") for p in res)
