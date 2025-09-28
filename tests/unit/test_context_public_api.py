import json
import tempfile
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.context import ContextManager, FixtureScope, MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.result import Result


def test_migration_config_roundtrip():
    cfg = MigrationConfig()
    d = cfg.to_dict()
    cfg2 = MigrationConfig.from_dict(d)
    assert cfg2.fixture_scope == cfg.fixture_scope


def test_pipeline_context_create_and_methods(tmp_path):
    src = tmp_path / "a.py"
    src.write_text("print(1)")
    ctx = PipelineContext.create(str(src))
    assert ctx.get_source_path().exists()
    # The implementation uses Path.with_suffix so the suffix will be the new suffix
    # Do not hard-code the suffix here; just ensure the target path has a suffix
    assert ctx.get_target_path().suffix != ""
    assert not ctx.is_dry_run()
    assert ctx.should_format_code()
    new_ctx = ctx.with_metadata("k", "v")
    assert new_ctx.metadata["k"] == "v"
    overridden = ctx.with_config(dry_run=True)
    assert overridden.is_dry_run()


def test_context_manager_load_config(tmp_path):
    # Missing file
    res = ContextManager.load_config_from_file(str(tmp_path / "nofile.yaml"))
    assert isinstance(res, Result)
    assert not res.is_success()

    # Valid YAML
    cfg = MigrationConfig()
    f = tmp_path / "c.yaml"
    # JSON can't directly serialize FixtureScope enum, convert to dict with string value
    d = cfg.to_dict()
    # Ensure fixture_scope is a simple string that matches the enum values
    d["fixture_scope"] = "function"
    f.write_text(json.dumps(d))
    res2 = ContextManager.load_config_from_file(str(f))
    # since we used json, yaml.safe_load will parse it into dict
    assert res2.is_success()


def test_validate_config_warnings():
    cfg = MigrationConfig(line_length=10, report_format="xml")
    res = ContextManager.validate_config(cfg)
    # Expect a warning due to report_format='xml' not being supported
    assert not res.is_success()
    assert isinstance(res, Result)
