import dataclasses
import json
import tempfile
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.context import (
    ContextManager,
    FixtureScope,
    MigrationConfig,
    PipelineContext,
)
from splurge_unittest_to_pytest.result import Result


def test_migration_config_override_and_roundtrip():
    cfg = MigrationConfig()
    cfg2 = cfg.with_override(max_file_size_mb=42, dry_run=True)
    assert cfg2.max_file_size_mb == 42
    assert cfg2.dry_run is True

    d = cfg2.to_dict()
    cfg3 = MigrationConfig.from_dict(d)
    assert cfg3.max_file_size_mb == 42
    assert cfg3.dry_run is True


def test_from_dict_validation_rejects_bad_format():
    with pytest.raises(ValueError):
        MigrationConfig.from_dict({"line_length": 10})  # too small should trigger validation


def test_pipeline_context_create_and_helpers(tmp_path):
    src = tmp_path / "source.py"
    src.write_text("# test file")

    cfg = MigrationConfig(dry_run=True)
    ctx = PipelineContext.create(source_file=str(src), config=cfg)
    assert ctx.get_source_path() == Path(str(src))
    assert ctx.is_dry_run() is True
    assert isinstance(ctx.run_id, str)

    # with_metadata should add without mutating original
    ctx2 = ctx.with_metadata("k", "v")
    assert ctx.metadata == {}
    assert ctx2.metadata["k"] == "v"

    # with_config returns a new context with modified config
    ctx3 = ctx.with_config(max_file_size_mb=5)
    assert ctx3.config.max_file_size_mb == 5

    # formatting helpers
    assert isinstance(ctx.should_format_code(), bool)
    assert isinstance(ctx.get_line_length(), int)


def test_context_manager_load_config_from_nonexistent_file(tmp_path):
    res = ContextManager.load_config_from_file(str(tmp_path / "nope.yaml"))
    assert not res.is_success()
    assert "config_file" in res.metadata


def test_migration_config_roundtrip():
    cfg = MigrationConfig()
    d = cfg.to_dict()
    cfg2 = MigrationConfig.from_dict(d)
    # fixture_scope removed; ensure roundtrip preserves other keys
    assert cfg2.line_length == cfg.line_length


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

    # Valid YAML (we serialize as JSON since yaml.safe_load will parse JSON)
    cfg = MigrationConfig()
    f = tmp_path / "c.yaml"
    d = cfg.to_dict()
    # If fixture scope is expected as a string, ensure a simple value is used
    d["fixture_scope"] = "function"
    f.write_text(json.dumps(d))
    res2 = ContextManager.load_config_from_file(str(f))
    # since we used json, yaml.safe_load will parse it into dict
    assert res2.is_success()


def test_validate_config_warnings():
    # Use valid line_length but invalid report_format
    cfg = MigrationConfig(line_length=100, report_format="xml")
    res = ContextManager.validate_config(cfg)
    # Expect a warning due to report_format='xml' not being supported
    assert not res.is_success()
    assert isinstance(res, Result)
