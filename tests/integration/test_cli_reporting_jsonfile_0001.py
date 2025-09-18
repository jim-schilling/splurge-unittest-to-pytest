from click.testing import CliRunner
from splurge_unittest_to_pytest.cli import main as cli_main
from splurge_unittest_to_pytest.main import ConversionResult


def test_cli_json_file_writes_ndjson(monkeypatch, tmp_path):
    f = tmp_path / "int_test_file3.py"
    f.write_text("class A:\n    def test(self):\n        self.assertTrue(True)\n")

    def fake_convert_string(s, *, autocreate=True, pattern_config=None):
        return ConversionResult(original_code=s, converted_code=s, has_changes=False, errors=[])

    monkeypatch.setattr("splurge_unittest_to_pytest.main.convert_string", fake_convert_string, raising=False)

    out = tmp_path / "out.ndjson"
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--dry-run", "--json-file", str(out), str(f)])
    assert result.exit_code == 0
    # File should exist and contain at least one JSON line
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line.strip()]
    assert len(lines) >= 1
    import json

    rec = json.loads(lines[0])
    assert rec["path"].endswith("int_test_file3.py")


def test_cli_rejects_unsafe_json_file(monkeypatch, tmp_path):
    # Create a directory we will pretend is WINDIR/SYSTEMROOT and ensure
    # the CLI refuses to write inside it.
    system_dir = tmp_path / "Windows"
    system_dir.mkdir()

    # Monkeypatch environment variable to point to our fake system dir
    monkeypatch.setenv("WINDIR", str(system_dir))

    f = tmp_path / "int_test_file4.py"
    f.write_text("class A:\n    def test(self):\n        self.assertTrue(True)\n")

    # Use the real CLI; it should exit with non-zero when attempting to
    # write to a location inside WINDIR.
    out = system_dir / "out.ndjson"
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--dry-run", "--json-file", str(out), str(f)])
    assert result.exit_code != 0
    # File should not be created
    assert not out.exists()
