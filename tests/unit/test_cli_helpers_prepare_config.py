import pytest

from splurge_unittest_to_pytest.cli_helpers import _apply_defaults_to_config, prepare_config
from splurge_unittest_to_pytest.context import MigrationConfig


def test_prepare_config_returns_migration_config():
    cfg = prepare_config()
    assert isinstance(cfg, MigrationConfig)


def test_prepare_config_applies_defaults_non_interactive():
    questions = [
        {"key": "line_length", "default": 88},
        {"key": "max_depth", "default": 5},
    ]

    cfg = prepare_config(base_config=MigrationConfig(), interactive=False, questions=questions)
    assert cfg.line_length == 88
    assert cfg.max_depth == 5


def test_prepare_config_enhanced_validation_fallback(monkeypatch):
    # Simulate enhanced validation raising to force fallback to basic config
    from splurge_unittest_to_pytest import cli_helpers

    def fake_handle_enhanced(base, kwargs):
        raise RuntimeError("enhanced validation failed")

    monkeypatch.setattr(cli_helpers, "_handle_enhanced_validation_features", fake_handle_enhanced)

    cfg = prepare_config(base_config=MigrationConfig(), interactive=False, questions=None, enhanced_kwargs={})
    assert isinstance(cfg, MigrationConfig)
