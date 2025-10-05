"""Unit tests for CLI commands: generate_templates_cmd, error_recovery_cmd, configure_cmd."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

from splurge_unittest_to_pytest import cli


def test_generate_templates_cmd_creates_files(tmp_path, mocker, capsys):
    """generate_templates_cmd should write template files for each template returned by the manager."""

    # Create fake templates
    class FakeTemplate:
        def __init__(self, name, config_dict):
            self.name = name
            self.config_dict = config_dict

        def to_yaml(self):
            return "yaml: true\n"

    fake_templates = {
        "basic": FakeTemplate("basic", {"a": 1}),
        "advanced": FakeTemplate("advanced", {"b": 2}),
    }

    fake_manager = mocker.MagicMock()
    fake_manager.get_all_templates.return_value = fake_templates

    mocker.patch(
        "splurge_unittest_to_pytest.config_validation.get_configuration_template_manager",
        return_value=fake_manager,
    )

    out_dir = tmp_path / "tpls"
    cli.generate_templates_cmd(str(out_dir), "yaml")

    # Check files created
    files = list(out_dir.iterdir())
    assert any(f.name == "basic.yaml" for f in files)
    assert any(f.name == "advanced.yaml" for f in files)

    # Check output message
    captured = capsys.readouterr()
    assert "Generated" in captured.out


def test_error_recovery_cmd_reports_and_interactive(mocker, monkeypatch, capsys):
    """error_recovery_cmd should display suggestions, workflow, and handle interactive input."""

    # Mock reporter and its engines
    mock_reporter = mocker.MagicMock()
    mocker.patch("splurge_unittest_to_pytest.cli.ErrorReporter", return_value=mock_reporter)

    # Build fake suggestion and workflow
    fake_suggestion = mocker.MagicMock()
    fake_suggestion.category = "CONFIG"
    fake_suggestion.message = "Fix X"
    fake_suggestion.action = "Do X"
    fake_suggestion.examples = ["example1"]

    mock_reporter.suggestion_engine.generate_suggestions.return_value = [fake_suggestion]
    mock_reporter.severity_assessor.assess_severity.return_value = mocker.MagicMock(value="low")

    fake_step = mocker.MagicMock()
    fake_step.description = "Edit config"
    fake_step.action = "edit file"
    fake_step.examples = ["ex1"]
    fake_step.validation = "check"

    fake_workflow = mocker.MagicMock()
    fake_workflow.title = "Fix Config"
    fake_workflow.description = "Do this"
    fake_workflow.estimated_time = 5
    fake_workflow.success_rate = 0.8
    fake_workflow.steps = [fake_step]

    mock_reporter.get_recovery_workflow.return_value = fake_workflow

    # Simulate user input 'y' to proceed with the first recovery step
    monkeypatch.setattr("builtins.input", lambda: "y")

    cli.error_recovery_cmd("Config error: missing param", "auto", None, True, False)

    captured = capsys.readouterr()

    assert "Error Analysis" in captured.out
    assert "Suggestions (" in captured.out
    assert "Recovery Workflow" in captured.out
    assert "Executing step 1" in captured.out


def test_configure_cmd_analyze_and_build(mocker, monkeypatch, capsys):
    """configure_cmd should analyze project and create/save configuration when requested."""

    # Set up analyzer to return a deterministic analysis
    mock_analyzer = mocker.MagicMock()
    mock_analyzer.analyze_project.return_value = {
        "test_files": ["tests/test_foo.py"],
        "test_prefixes": {"test_"},
        "project_type": mocker.MagicMock(value="library"),
        "complexity_score": 3,
    }
    mocker.patch("splurge_unittest_to_pytest.cli.ProjectAnalyzer", return_value=mock_analyzer)

    # Builder returns a fake config object and interaction data
    fake_config = SimpleNamespace(target_root="out")

    fake_interaction = {"questions": [], "project_type": mocker.MagicMock(value="library")}
    mock_builder = mocker.MagicMock()
    mock_builder.build_configuration_interactive.return_value = (fake_config, fake_interaction)
    mocker.patch(
        "splurge_unittest_to_pytest.cli.InteractiveConfigBuilder",
        return_value=mock_builder,
    )

    # Manager returns a successful validation result
    mock_manager = mocker.MagicMock()
    mock_result = SimpleNamespace(success=True, config=fake_config, errors=[], warnings=[])
    mock_manager.validate_and_enhance_config.return_value = mock_result
    mocker.patch(
        "splurge_unittest_to_pytest.cli.IntegratedConfigurationManager",
        return_value=mock_manager,
    )

    # Run configure_cmd with output_file to trigger save path
    out_file = Path("test-config.yml")
    try:
        cli.configure_cmd(".", str(out_file), False, True)

        captured = capsys.readouterr()
        assert "Project analysis complete!" in captured.out
        assert "Configuration saved to" in captured.out or "Configuration ready!" in captured.out

    finally:
        if out_file.exists():
            out_file.unlink()


def test_generate_templates_cmd_unsupported_format(mocker, capsys):
    """Unsupported template format should exit with typer.Exit."""

    class FakeTemplate:
        def __init__(self, name):
            self.name = name

        def to_yaml(self):
            return "yaml: true\n"

    fake_manager = mocker.MagicMock()
    fake_manager.get_all_templates.return_value = {"basic": FakeTemplate("basic")}

    mocker.patch(
        "splurge_unittest_to_pytest.config_validation.get_configuration_template_manager",
        return_value=fake_manager,
    )

    with pytest.raises(typer.Exit):
        cli.generate_templates_cmd("./doesnt_matter", "xml")


def test_error_recovery_cmd_invalid_context(mocker, capsys):
    """When context JSON is invalid, warn and proceed with empty context."""

    mock_reporter = mocker.MagicMock()
    mock_reporter.suggestion_engine.generate_suggestions.return_value = []
    mock_reporter.get_recovery_workflow.return_value = None
    mock_reporter.severity_assessor.assess_severity.return_value = mocker.MagicMock(value="low")

    mocker.patch("splurge_unittest_to_pytest.cli.ErrorReporter", return_value=mock_reporter)

    # Pass invalid JSON context
    cli.error_recovery_cmd("Some file error", "auto", "{not: valid}", False, False)

    captured = capsys.readouterr()
    assert "Warning: Invalid JSON context" in captured.out or "No specific suggestions available" in captured.out


def test_configure_cmd_validation_failure(mocker, monkeypatch, capsys, tmp_path):
    """configure_cmd should display validation errors and warnings when validation fails."""

    # Analyzer
    mock_analyzer = mocker.MagicMock()
    mock_analyzer.analyze_project.return_value = {
        "test_files": [],
        "test_prefixes": set(),
        "project_type": mocker.MagicMock(value="library"),
        "complexity_score": 1,
    }
    mocker.patch("splurge_unittest_to_pytest.cli.ProjectAnalyzer", return_value=mock_analyzer)

    # Builder
    fake_config = SimpleNamespace(target_root="out")
    fake_interaction = {"questions": [], "project_type": mocker.MagicMock(value="library")}
    mock_builder = mocker.MagicMock()
    mock_builder.build_configuration_interactive.return_value = (fake_config, fake_interaction)
    mocker.patch(
        "splurge_unittest_to_pytest.cli.InteractiveConfigBuilder",
        return_value=mock_builder,
    )

    # Manager returns failure
    mock_manager = mocker.MagicMock()
    mock_result = SimpleNamespace(success=False, config=None, errors=[{"message": "Invalid X"}], warnings=["W1"])
    mock_manager.validate_and_enhance_config.return_value = mock_result
    mocker.patch(
        "splurge_unittest_to_pytest.cli.IntegratedConfigurationManager",
        return_value=mock_manager,
    )

    # Run
    # Run and assert printed errors/warnings
    cli.configure_cmd(str(tmp_path), None, False, False)
    captured = capsys.readouterr()
    assert "Configuration validation failed:" in captured.out
    assert "- Invalid X" in captured.out
    assert "Warnings:" in captured.out
