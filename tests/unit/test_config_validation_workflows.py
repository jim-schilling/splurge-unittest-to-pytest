"""Tests focused on configuration workflows and project analyzer detection.

Targets: InteractiveConfigBuilder._custom_setup_workflow, _unknown_project_workflow,
_build_question_tree, and ProjectAnalyzer._detect_project_type behavior.
"""

from pathlib import Path

import pytest

from splurge_unittest_to_pytest.config_validation import (
    InteractiveConfigBuilder,
    ProjectAnalyzer,
    ProjectType,
)


def test_custom_setup_workflow_structure_and_processing():
    builder = InteractiveConfigBuilder()
    config, interaction = builder._custom_setup_workflow()

    assert interaction["project_type"] == ProjectType.CUSTOM_SETUP
    assert "questions" in interaction

    # Find the file_patterns question and test its process function
    qp = None
    for q in interaction["questions"]:
        if q.get("key") == "file_patterns":
            qp = q
            break

    assert qp is not None
    # process should split comma-separated values
    processed = qp["process"]("test_*.py, spec_*.py")
    assert isinstance(processed, list)
    assert "test_*.py" in processed and "spec_*.py" in processed


def test_unknown_project_workflow_changes_title():
    builder = InteractiveConfigBuilder()
    config, interaction = builder._unknown_project_workflow()
    assert interaction["title"] == "Unknown Project Type Configuration"


def test_build_question_tree_contains_expected_keys():
    builder = InteractiveConfigBuilder()
    tree = builder._build_question_tree()
    assert "project_detection" in tree
    assert "backup_strategy" in tree
    assert "output_strategy" in tree
    assert "options" in tree["project_detection"]


def test_detect_project_type_with_spec_files(tmp_path, monkeypatch):
    # Create a spec file in tmp_path and ensure detection reads it via builder
    monkeypatch.chdir(tmp_path)
    p = tmp_path / "spec_example.py"
    p.write_text("def spec_one(): pass")

    builder = InteractiveConfigBuilder()
    proj_type = builder._detect_project_type()
    assert proj_type == ProjectType.MODERN_FRAMEWORK


def test_detect_project_type_with_many_test_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Create 6 test files to exceed the threshold (>5)
    for i in range(6):
        f = tmp_path / f"test_{i}.py"
        f.write_text("def test_sample(): pass")

    builder = InteractiveConfigBuilder()
    proj_type = builder._detect_project_type()
    assert proj_type == ProjectType.LEGACY_TESTING


def test_detect_project_type_default_custom_setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # No test files should result in CUSTOM_SETUP
    builder = InteractiveConfigBuilder()
    proj_type = builder._detect_project_type()
    assert proj_type == ProjectType.CUSTOM_SETUP


def test_build_configuration_interactive_routes(monkeypatch):
    builder = InteractiveConfigBuilder()

    # Force _detect_project_type to return each ProjectType and assert the project_type in interaction
    for pt in [ProjectType.LEGACY_TESTING, ProjectType.MODERN_FRAMEWORK, ProjectType.CUSTOM_SETUP]:
        monkeypatch.setattr(builder, "_detect_project_type", (lambda p=pt: p))
        cfg, interaction = builder.build_configuration_interactive()
        assert interaction["project_type"] == pt
