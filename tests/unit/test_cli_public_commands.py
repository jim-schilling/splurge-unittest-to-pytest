import builtins
from types import SimpleNamespace

import pytest

import splurge_unittest_to_pytest.cli as cli_mod


def test_version_command(monkeypatch, capsys):
    # Monkeypatch package-level version used by cli.version()
    import splurge_unittest_to_pytest as pkg

    monkeypatch.setattr(pkg, "__version__", "0.1.0")
    cli_mod.version()
    captured = capsys.readouterr()
    assert "splurge-unittest-to-pytest 0.1.0" in captured.out


def test_generate_docs_invalid_format_raises(monkeypatch):
    import typer

    with pytest.raises(typer.Exit):
        cli_mod.generate_docs_cmd(format="xml")


def test_list_templates_cmd(monkeypatch, capsys):
    # Monkeypatch template functions to return a small set
    monkeypatch.setattr(cli_mod, "list_available_templates", lambda: ["basic"])

    class T:
        name = "basic"

        description = "desc"

        def to_yaml(self):
            return "yaml"

        def to_cli_args(self):
            return "--config basic"

    monkeypatch.setattr(cli_mod, "get_template", lambda name: T())
    cli_mod.list_templates_cmd()
    out = capsys.readouterr().out
    assert "Available configuration templates" in out
