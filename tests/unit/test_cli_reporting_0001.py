from click.testing import CliRunner

from splurge_unittest_to_pytest.cli import main as cli_main
from splurge_unittest_to_pytest.main import ConversionResult


def test_dry_run_json_and_diff(monkeypatch, tmp_path):
    f = tmp_path / "test_file.py"
    src = "class A:\n    def test(self):\n        self.assertEqual(1, 1)\n"
    f.write_text(src)

    def fake_convert_string(s, *, autocreate=True, pattern_config=None):
        # produce a changed result
        converted = s.replace("self.assertEqual(1, 1)", "assert 1 == 1")
        return ConversionResult(original_code=s, converted_code=converted, has_changes=True, errors=[])

    monkeypatch.setattr("splurge_unittest_to_pytest.main.convert_string", fake_convert_string, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, ["--dry-run", "--json", "--diff", str(f)])
    assert result.exit_code == 0
    # Expect NDJSON line(s)
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) >= 1
    import json

    # First non-empty line should be a JSON object
    record = json.loads(lines[0])
    assert record["path"].endswith("test_file.py")
    assert record["changed"] is True
    assert "summary" in record
    assert record["summary"].get("diff") is not None
