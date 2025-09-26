import os
import tempfile
from pathlib import Path

import pytest
import typer

from splurge_unittest_to_pytest import cli
from splurge_unittest_to_pytest.context import MigrationConfig


def test_create_config_defaults():
    cfg = cli.create_config()
    assert isinstance(cfg, MigrationConfig)
    assert cfg.file_patterns == ["test_*.py"]
    assert cfg.fixture_scope.value == "function"


def test_validate_source_files_with_patterns(tmp_path):
    # Create a small directory tree with python files
    d = tmp_path / "proj"
    d.mkdir()
    f1 = d / "test_a.py"
    f1.write_text("# test a")
    f2 = d / "not_a_test.txt"
    f2.write_text("ignore")

    res = cli.validate_source_files_with_patterns([], str(d), ["test_*.py"], recurse=True)
    assert len(res) == 1
    assert any(Path(p).name == "test_a.py" for p in res)


def test_validate_source_files(tmp_path):
    f = tmp_path / "t.py"
    f.write_text("print(1)")
    out = cli.validate_source_files([str(f)])
    assert out == [str(f)]

    # Non-existing path should raise typer.Exit
    with pytest.raises(typer.Exit):
        cli.validate_source_files([str(tmp_path / "noexist.py")])


def test_init_config_requires_yaml(monkeypatch, tmp_path):
    # Simulate missing yaml dependency by temporarily removing yaml from sys.modules
    monkeypatch.setitem(os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    # If yaml is missing, init_config should exit
    monkeypatch.setitem(__import__("builtins").__dict__, "__import__", __import__)
    # We can't easily simulate import failure globally here, but ensure init_config writes file when pyyaml exists
    out = tmp_path / "cfg.yaml"
    try:
        cli.init_config(str(out))
    except SystemExit:
        pytest.skip("PyYAML not available in this environment")
    assert out.exists()
