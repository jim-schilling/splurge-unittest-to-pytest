from click.testing import CliRunner
from splurge_unittest_to_pytest import cli


def test_cli_dry_run_respects_patterns(tmp_path, monkeypatch):
    # Create a temp file that looks like a unittest TestCase but uses a
    # custom setup method 'custom_setup' that we'll pass via CLI flags.
    src = """
import unittest

class TestX(unittest.TestCase):
    def custom_setup(self):
        self.x = 1

    def test_foo(self):
        assert self.x == 1
"""
    file_path = tmp_path / "test_x.py"
    file_path.write_text(src, encoding="utf-8")

    runner = CliRunner()

    # Run CLI in dry-run mode and pass --setup-methods custom_setup
    result = runner.invoke(cli.main, [str(file_path), "--dry-run", "--setup-methods", "custom_setup"])
    assert result.exit_code == 0
    # Output should include "Would convert" because the custom setup should be recognized
    assert "Would convert" in result.output
