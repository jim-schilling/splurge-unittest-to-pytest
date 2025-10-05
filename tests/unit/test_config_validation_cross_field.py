import pytest

from splurge_unittest_to_pytest.config_validation import (
    EnhancedConfigurationResult,
    IntegratedConfigurationManager,
    ValidatedMigrationConfig,
)
from splurge_unittest_to_pytest.context import MigrationConfig


def test_validate_cross_field_incompatible_flags():
    # Construct a validated config that violates cross-field compatibility:
    # dry_run=True with target_root should be flagged by the model-level validator.
    with pytest.raises(ValueError) as exc:
        ValidatedMigrationConfig(dry_run=True, target_root="/tmp/out")

    assert "Configuration conflicts detected" in str(exc.value)


def test_integrated_manager_enhance_warns_or_returns(monkeypatch, tmp_path):
    # IntegratedConfigurationManager.validate_and_enhance_config should return
    # an EnhancedConfigurationResult describing success or warnings/errors.

    mgr = IntegratedConfigurationManager()

    # Provide lightweight analyzer/advisor fakes used by the manager
    class FakeAnalyzer:
        def detect_use_case(self, cfg):
            return "basic_migration"

    class FakeAdvisor:
        def suggest_improvements(self, cfg):
            return []

    mgr.analyzer = FakeAnalyzer()
    mgr.advisor = FakeAdvisor()

    # Valid config: basic defaults (use dict input expected by manager)
    base = MigrationConfig().to_dict()
    result = mgr.validate_and_enhance_config(base)
    assert isinstance(result, EnhancedConfigurationResult)
    assert result.success is True

    # Invalid: set an impossible file size (violates ge=1)
    bad = MigrationConfig().to_dict()
    bad["max_file_size_mb"] = -1
    result2 = mgr.validate_and_enhance_config(bad)
    assert isinstance(result2, EnhancedConfigurationResult)
    assert result2.success is False
    assert result2.errors


def test_integrated_manager_filesystem_checks(tmp_path):
    mgr = IntegratedConfigurationManager()

    class FakeAnalyzer:
        def detect_use_case(self, cfg):
            return "enterprise_deployment"

    class FakeAdvisor:
        def suggest_improvements(self, cfg):
            return []

    mgr.analyzer = FakeAnalyzer()
    mgr.advisor = FakeAdvisor()

    # Case: target_root does not exist and dry_run is False -> should produce a warning
    cfg = MigrationConfig().to_dict()
    cfg["target_root"] = str(tmp_path / "no_such_dir")
    cfg["dry_run"] = False
    res = mgr.validate_and_enhance_config(cfg)
    assert isinstance(res, EnhancedConfigurationResult)
    assert res.success is False
    assert res.warnings

    # Case: backup_root specified but backup_originals disabled -> model-level
    # validation raises and the manager returns an EnhancedConfigurationResult
    # with errors (not warnings).
    cfg2 = MigrationConfig().to_dict()
    cfg2["backup_root"] = str(tmp_path / "backup_dir")
    cfg2["backup_originals"] = False
    res2 = mgr.validate_and_enhance_config(cfg2)
    assert isinstance(res2, EnhancedConfigurationResult)
    assert res2.success is False
    assert res2.errors
