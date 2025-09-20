from click.testing import CliRunner

from splurge_unittest_to_pytest.cli import main as cli_main
from splurge_unittest_to_pytest.main import ConversionResult


def test_cli_ndjson_only(monkeypatch, tmp_path):
    # Create a test file
    f = tmp_path / "int_test_file.py"
    src = "class A:\n    def test(self):\n        self.assertTrue(True)\n"
    f.write_text(src)

    def fake_convert_string(s, *, autocreate=True, pattern_config=None):
        # simulate no diff (unchanged)
        return ConversionResult(original_code=s, converted_code=s, has_changes=False, errors=[])

    monkeypatch.setattr("splurge_unittest_to_pytest.main.convert_string", fake_convert_string, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, ["--dry-run", "--json", str(f)])
    assert result.exit_code == 0
    # Expect NDJSON line for the file (even if unchanged)
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) >= 1
    import json

    # Find the first JSON-parsable line (NDJSON may be mixed with warnings)
    rec = None
    for line in lines:
        try:
            rec = json.loads(line)
            break
        except Exception:
            continue
    assert rec is not None, f"No JSON record found in output:\n{result.output}"
    assert rec["path"].endswith("int_test_file.py")
    assert rec["changed"] is False
    assert rec["errors"] == []


def test_cli_json_and_diff_combined(monkeypatch, tmp_path):
    f = tmp_path / "int_test_file2.py"
    src = "class A:\n    def test(self):\n        self.assertEqual(1,1)\n"
    f.write_text(src)

    def fake_convert_string(s, *, autocreate=True, pattern_config=None):
        converted = s.replace("self.assertEqual(1,1)", "assert 1 == 1")
        return ConversionResult(original_code=s, converted_code=converted, has_changes=True, errors=[])

    monkeypatch.setattr("splurge_unittest_to_pytest.main.convert_string", fake_convert_string, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, ["--dry-run", "--json", "--diff", str(f)])
    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) >= 1
    import json

    rec = None
    for line in lines:
        try:
            rec = json.loads(line)
            break
        except Exception:
            continue
    assert rec is not None, f"No JSON record found in output:\n{result.output}"
    assert rec["changed"] is True
    assert rec["summary"].get("diff") is not None
