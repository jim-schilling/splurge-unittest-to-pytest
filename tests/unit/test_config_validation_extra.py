"""Extra unit tests for config_validation to exercise validators, detectors, templates, and manager flows."""

import os
from pathlib import Path

import pytest

from splurge_unittest_to_pytest import config_validation as cv
from splurge_unittest_to_pytest.config_validation import (
    ConfigurationAdvisor,
    ConfigurationTemplate,
    ConfigurationTemplateManager,
    ConfigurationUseCaseDetector,
    EnhancedConfigurationResult,
    IntegratedConfigurationManager,
    ProjectAnalyzer,
    Suggestion,
    SuggestionType,
    create_validated_config,
)


def test_cross_field_validator_raises_for_conflicts():
    # dry_run with target_root should trigger cross-field conflict in model validator
    with pytest.raises(Exception) as exc:
        create_validated_config(dry_run=True, target_root="/tmp/out")

    assert "Configuration conflicts detected" in str(exc.value)


def test_detect_use_case_ci_and_production():
    cfg = create_validated_config(
        dry_run=False, fail_fast=True, max_concurrent_files=4, cache_analysis_results=True, max_file_size_mb=20
    )

    use_case = cv.detect_configuration_use_case(cfg)
    assert use_case == cv.ConfigurationProfile.CI_INTEGRATION

    prod_cfg = create_validated_config(
        dry_run=False, fail_fast=True, degradation_tier="essential", backup_originals=True
    )
    prod_use = cv.detect_configuration_use_case(prod_cfg)
    assert prod_use == cv.ConfigurationProfile.PRODUCTION_DEPLOYMENT


def test_configuration_advisor_suggests_performance_and_safety():
    # Use a large-but-valid file size that doesn't trigger cross-field validator (>50 triggers model_validator)
    cfg = create_validated_config(max_file_size_mb=30, max_concurrent_files=1)
    suggestions = cv.generate_configuration_suggestions(cfg)
    # Expect at least one performance suggestion for >20MB with single concurrency
    assert any(s.type == SuggestionType.PERFORMANCE for s in suggestions)

    # Safety suggestions for experimental tier without dry_run would normally be blocked by cross-field validation
    # So call the advisor's safety generator directly with a simple namespace to assert behavior
    fake_cfg = type("C", (), {})()
    fake_cfg.degradation_tier = "experimental"
    fake_cfg.dry_run = False
    fake_cfg.backup_originals = True
    safety_suggestions = ConfigurationAdvisor()._generate_safety_suggestions(fake_cfg)
    assert any(s.type == SuggestionType.SAFETY for s in safety_suggestions)


def test_configuration_field_registry_and_help():
    registry = cv.get_configuration_field_registry()
    field = registry.get_field("target_root")
    assert field is not None
    help_text = cv.get_field_help("target_root")
    assert "target_root" in help_text

    missing = cv.get_field_help("no_such_field")
    assert "No documentation available" in missing


def test_generate_documentation_markdown_and_html_and_invalid():
    md = cv.generate_configuration_documentation("markdown")
    assert md.startswith("# Configuration Reference")

    html = cv.generate_configuration_documentation("html")
    assert html.startswith("<!DOCTYPE html>")

    with pytest.raises(ValueError):
        cv.generate_configuration_documentation("xml")


def test_configuration_template_yaml_and_cli_args():
    tmpl = ConfigurationTemplate(
        "T1", "desc", {"dry_run": True, "file_patterns": ["test_*.py"]}, cv.ConfigurationProfile.BASIC_MIGRATION
    )
    y = tmpl.to_yaml()
    assert "# T1" in y
    args = tmpl.to_cli_args()
    # dry_run True should produce a flag, file_patterns should produce key=value entries
    assert "--dry-run" in args or "--dry-run" in y
    assert "--file-patterns=test_*.py" in args


def test_template_manager_getters_and_suggest(tmp_path):
    mgr = ConfigurationTemplateManager()
    names = mgr.get_template_names()
    assert "ci_integration" in names

    cfg = create_validated_config(dry_run=False, fail_fast=True, max_concurrent_files=8)
    suggested = mgr.suggest_template_for_config(cfg)
    # For CI-like config, expect a suggestion
    assert suggested is not None

    # generate_config_from_template valid and invalid
    cfg_dict = cv.generate_config_from_template("basic_migration")
    assert isinstance(cfg_dict, dict)

    with pytest.raises(ValueError):
        cv.generate_config_from_template("nope_template")


def test_project_analyzer_helpers():
    pa = ProjectAnalyzer()
    content = """
def test_one():
    pass

def spec_two():
    pass

def should_three():
    pass

def it_four():
    pass
"""
    prefixes = pa._extract_test_prefixes(content)
    assert "test_" in prefixes or "spec_" in prefixes
    assert pa._has_setup_methods("def setUp(self): pass")

    many_classes = "\n".join([f"class A{i}: pass" for i in range(5)])
    assert pa._has_nested_classes(many_classes)


def test_integrated_manager_validation_and_filesystem(tmp_path):
    mgr = IntegratedConfigurationManager()
    mgr.analyzer = ConfigurationUseCaseDetector()
    mgr.advisor = ConfigurationAdvisor()

    # Validation errors: empty file_patterns triggers validation error
    res = mgr.validate_and_enhance_config({"file_patterns": []})
    assert res.success is False
    assert res.errors is not None

    # Filesystem issues: non-existent target_root when dry_run=False
    target = tmp_path / "nonexistent_dir"
    cfg = {
        "target_root": str(target),
        "dry_run": False,
        "backup_originals": True,
        "backup_root": str(tmp_path / "no_backup_dir"),
    }
    res2 = mgr.validate_and_enhance_config(cfg)
    assert res2.success is False
    assert res2.warnings is not None
    assert any("does not exist" in w for w in res2.warnings)


def test_manager_error_categorize_and_result_to_dict():
    mgr = IntegratedConfigurationManager()
    cat = mgr._categorize_validation_errors(ValueError("cross-field issue detected"))
    assert cat and cat[0]["type"] == "cross_field_validation"

    res = EnhancedConfigurationResult(
        success=True,
        config=create_validated_config(),
        suggestions=[Suggestion(SuggestionType.ACTION, "m", "a")],
        use_case_detected="basic",
    )
    d = res.to_dict()
    assert d["success"] is True
    assert "suggestions" in d
