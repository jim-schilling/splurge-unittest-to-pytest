import builtins
from pathlib import Path

import pytest
import typer

from splurge_unittest_to_pytest import cli as cli_module
from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.result import Result


def test_migrate_config_file_load_failure(monkeypatch, tmp_path, capsys):
    # Simulate ContextManager.load_config_from_file raising an exception
    def _load(path):
        raise RuntimeError("could not read config")

    monkeypatch.setattr(cli_module.ContextManager, "load_config_from_file", staticmethod(_load))

    with pytest.raises(typer.Exit):
        # call migrate with a config file to force the load path
        cli_module.migrate([str(tmp_path)], config_file=str(tmp_path / "cfg.yaml"), info=False, debug=False)


def test_migrate_delegates_to_main_on_success(monkeypatch, tmp_path):
    # Make load_config_from_file return a successful MigrationConfig
    monkeypatch.setattr(
        cli_module.ContextManager,
        "load_config_from_file",
        staticmethod(lambda p: Result.success(MigrationConfig())),
    )

    # Make validate_source_files_with_patterns return a single file
    monkeypatch.setattr(cli_module, "validate_source_files_with_patterns", lambda s, r, p, rec: ["a.py"])

    # Provide a real event bus so subscribers can register
    from splurge_unittest_to_pytest.events import EventBus

    monkeypatch.setattr(cli_module, "create_event_bus", lambda: EventBus())

    called = {}

    def fake_migrate(files, config=None, event_bus=None):
        called["files"] = list(files)
        called["config"] = config
        return Result.success(["outfile.py"])

    monkeypatch.setattr(cli_module.main_module, "migrate", fake_migrate)

    # Should not raise - pass explicit flags to avoid OptionInfo truthiness
    cli_module.migrate(["tests/"], config_file=None, info=False, debug=False)

    assert called["files"] == ["a.py"]


def test_generate_docs_invalid_format_raises():
    with pytest.raises(typer.Exit):
        cli_module.generate_docs_cmd(format="xml")
