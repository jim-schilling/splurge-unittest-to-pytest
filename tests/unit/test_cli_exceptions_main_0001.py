from click.testing import CliRunner

from splurge_unittest_to_pytest.cli import main as cli_main
from splurge_unittest_to_pytest.exceptions import ParseError
from splurge_unittest_to_pytest.main import ConversionResult


def test_dry_run_verbose_shows_diff_and_summary(monkeypatch, tmp_path):
    f = tmp_path / "t.py"
    f.write_text("class A:\n    pass\n")

    def fake_convert_string(src, *, autocreate=True, pattern_config=None):
        return ConversionResult(original_code=src, converted_code="import pytest\n" + src, has_changes=True, errors=[])

    monkeypatch.setattr("splurge_unittest_to_pytest.main.convert_string", fake_convert_string, raising=False)
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--dry-run", "--verbose", str(f)])
    assert result.exit_code == 0
    assert "Would convert" in result.output
    assert "Added pytest import" in result.output or "Lines changed" in result.output


def test_backup_creation_and_warning_on_failure(monkeypatch, tmp_path):
    f = tmp_path / "t2.py"
    f.write_text("print(2)")
    backup_dir = tmp_path / "bak"

    def fake_convert_file(
        file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns
    ):
        return ConversionResult(original_code="a", converted_code="b", has_changes=True, errors=[])

    monkeypatch.setattr("splurge_unittest_to_pytest.cli.convert_file", fake_convert_file, raising=False)

    def fake_copy2(src, dst):
        raise Exception("copy failed")

    monkeypatch.setattr("shutil.copy2", fake_copy2)
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--backup", str(backup_dir), str(f)])
    assert result.exit_code == 0 or result.exit_code == 1
    assert "Failed to create backup" in result.output or "Warning:" in result.output


def test_pattern_configurator_verbose_output(monkeypatch, tmp_path):
    f = tmp_path / "t3.py"
    f.write_text("print(3)")

    def fake_convert_file(
        file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns
    ):
        return ConversionResult(original_code="a", converted_code="a", has_changes=False, errors=[])

    monkeypatch.setattr("splurge_unittest_to_pytest.cli.convert_file", fake_convert_file, raising=False)
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--verbose", "--setup-methods", "setUp, prepare", str(f)])
    assert result.exit_code == 0
    assert "Using custom method patterns" in result.output or "Setup:" in result.output


def test_dry_run_parse_error_is_handled(monkeypatch, tmp_path):
    f = tmp_path / "t4.py"
    f.write_text("x")

    def fake_convert_string(src, *, autocreate=True, pattern_config=None):
        raise ParseError("bad parse")

    monkeypatch.setattr("splurge_unittest_to_pytest.main.convert_string", fake_convert_string, raising=False)
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--dry-run", str(f)])
    assert result.exit_code == 1
    assert "Error processing" in result.output or "Error in" in result.output
