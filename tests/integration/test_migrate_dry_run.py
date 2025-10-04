import os
import tempfile

from typer.testing import CliRunner

from splurge_unittest_to_pytest import cli

runner = CliRunner()


def test_migrate_dry_run_creates_output_and_reports():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple unittest file
        src = os.path.join(tmpdir, "test_sample.py")
        with open(src, "w", encoding="utf-8") as f:
            f.write(
                """
import unittest

class SampleTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1 + 1, 2)
"""
            )

        # Run the CLI migrate command in dry-run mode
        result = runner.invoke(cli.app, ["migrate", src, "--dry-run", "--no-format"])

        # Ensure command succeeded
        assert result.exit_code == 0
        # Expect some dry-run info printed
        assert "Dry-run mode enabled" in result.output or "PYTEST:" in result.output or "== PYTEST:" in result.output
