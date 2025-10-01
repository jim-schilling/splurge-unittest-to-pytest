import subprocess
from pathlib import Path

SAMPLE_SOURCE = """import unittest


class ExampleTest(unittest.TestCase):
    def test_one(self):
        self.assertEqual(1, 1)

"""


def run_cli_migrate(args, cwd=None):
    cmd = ["python", "-m", "splurge_unittest_to_pytest.cli", "migrate"] + args
    # Use subprocess.run to invoke the CLI similarly to a user
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res


def test_cli_backup_default(tmp_path: Path):
    src = tmp_path / "test_cli_sample.py"
    src.write_text(SAMPLE_SOURCE, encoding="utf-8")

    # Run CLI without --skip-backup (default: create backup)
    res = run_cli_migrate([str(src)])
    assert res.returncode == 0, f"CLI failed: {res.stderr}\n{res.stdout}"

    backup_path = src.with_suffix(src.suffix + ".backup")
    assert backup_path.exists(), "Expected .backup file to be created by default via CLI"


def test_cli_skip_backup_flag(tmp_path: Path):
    src = tmp_path / "test_cli_sample2.py"
    src.write_text(SAMPLE_SOURCE, encoding="utf-8")

    # Run CLI with --skip-backup to disable backup creation
    res = run_cli_migrate([str(src), "--skip-backup"])
    assert res.returncode == 0, f"CLI failed: {res.stderr}\n{res.stdout}"

    backup_path = src.with_suffix(src.suffix + ".backup")
    assert not backup_path.exists(), "Did not expect .backup file when --skip-backup passed"
