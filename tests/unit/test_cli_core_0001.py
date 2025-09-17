from click.testing import CliRunner
from splurge_unittest_to_pytest import cli


def test_cli_dry_run_respects_patterns(tmp_path, monkeypatch):
    src = "\nimport unittest\n\nclass TestX(unittest.TestCase):\n    def custom_setup(self):\n        self.x = 1\n\n    def test_foo(self):\n        assert self.x == 1\n"
    file_path = tmp_path / "test_x.py"
    file_path.write_text(src, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli.main, [str(file_path), "--dry-run", "--setup-methods", "custom_setup"])
    assert result.exit_code == 0
    assert "Would convert" in result.output
