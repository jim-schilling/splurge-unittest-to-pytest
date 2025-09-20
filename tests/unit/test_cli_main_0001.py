from click.testing import CliRunner

from splurge_unittest_to_pytest.cli import main as cli_main
from splurge_unittest_to_pytest.main import ConversionResult


def test_no_paths_exits_with_error():
    runner = CliRunner()
    result = runner.invoke(cli_main, [])
    assert result.exit_code == 1
    assert "Error: No paths provided" in result.output


def test_directory_without_recursive_warns_and_no_files(tmp_path, monkeypatch):
    d = tmp_path / "dir"
    d.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli_main, [str(d)])
    assert result.exit_code == 0
    assert "Warning:" in result.output or "No unittest files found" in result.output


def test_dry_run_calls_convert_string_and_reports(monkeypatch, tmp_path):
    f = tmp_path / "test_file.py"
    f.write_text("print(1)")
    called = {}

    def fake_convert_string(src, *, autocreate=True, pattern_config=None):
        called["src"] = src
        return ConversionResult(original_code=src, converted_code=src, has_changes=False, errors=[])

    monkeypatch.setattr("splurge_unittest_to_pytest.cli.convert_string", fake_convert_string, raising=False)
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--dry-run", str(f)])
    assert result.exit_code == 0
    assert "0 files would be converted" in result.output
    assert "1 files unchanged" in result.output


def test_convert_file_error_is_reported(monkeypatch, tmp_path):
    f = tmp_path / "test_file.py"
    f.write_text("bad")

    def fake_convert_file(
        file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns
    ):
        return ConversionResult(original_code="a", converted_code="b", has_changes=False, errors=["parse error"])

    monkeypatch.setattr("splurge_unittest_to_pytest.cli.convert_file", fake_convert_file, raising=False)
    runner = CliRunner()
    result = runner.invoke(cli_main, [str(f)])
    assert result.exit_code == 1
    assert "files had errors" in result.output or "Error in" in result.output
