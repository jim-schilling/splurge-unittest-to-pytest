import textwrap
from pathlib import Path

import typer
from typer.testing import CliRunner

from splurge_unittest_to_pytest import cli


def _write_sample(tmp_path: Path) -> Path:
    src = tmp_path / "sample_unittest.py"
    src.write_text(
        textwrap.dedent(
            """
            import unittest

            class T(unittest.TestCase):
                def test_a(self):
                    self.assertTrue(True)
            """
        ),
        encoding="utf-8",
    )
    return src


def test_cli_dry_run_prints_pytest_header(tmp_path: Path):
    runner = CliRunner()
    src = _write_sample(tmp_path)

    result = runner.invoke(cli.app, ["migrate", str(src), "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    out = result.stdout
    # Expect the default printing header (contains the PYTEST header and the sample file name)
    assert "== PYTEST:" in out
    assert "sample_unittest" in out


def test_cli_dry_run_diff_mode_prints_diff_header(tmp_path: Path):
    runner = CliRunner()
    src = _write_sample(tmp_path)

    result = runner.invoke(cli.app, ["migrate", str(src), "--dry-run", "--diff"], catch_exceptions=False)
    assert result.exit_code == 0
    out = result.stdout
    assert "== DIFF:" in out
    assert "sample_unittest" in out


def test_cli_dry_run_list_mode_prints_files_header(tmp_path: Path):
    runner = CliRunner()
    src = _write_sample(tmp_path)

    result = runner.invoke(cli.app, ["migrate", str(src), "--dry-run", "--list"], catch_exceptions=False)
    assert result.exit_code == 0
    out = result.stdout
    assert "== FILES:" in out
    assert "sample_unittest" in out
