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


def test_cli_backup_root_option(tmp_path: Path):
    """Test that the --backup-root CLI option creates backups in the specified directory."""
    src = tmp_path / "test_cli_sample3.py"
    src.write_text(SAMPLE_SOURCE, encoding="utf-8")

    # Specify a custom backup root directory
    backup_root = tmp_path / "custom_backups"

    # Run CLI with --backup-root option
    res = run_cli_migrate([str(src), "--backup-root", str(backup_root)])
    assert res.returncode == 0, f"CLI failed: {res.stderr}\n{res.stdout}"

    # Backup should be created in the backup_root directory, not next to source
    expected_backup = backup_root / src.name
    backup_path = expected_backup.with_suffix(expected_backup.suffix + ".backup")
    assert backup_path.exists(), f"Expected backup in backup_root: {backup_path}"

    # Original location should not have a backup
    original_backup = src.with_suffix(src.suffix + ".backup")
    assert not original_backup.exists(), "Did not expect backup next to source file"


def test_cli_backup_root_creates_directory(tmp_path: Path):
    """Test that --backup-root creates the directory if it doesn't exist."""
    src = tmp_path / "test_cli_sample4.py"
    src.write_text(SAMPLE_SOURCE, encoding="utf-8")

    # Specify a backup root that doesn't exist yet
    backup_root = tmp_path / "new_backups" / "subdir"

    # Run CLI with --backup-root option
    res = run_cli_migrate([str(src), "--backup-root", str(backup_root)])
    assert res.returncode == 0, f"CLI failed: {res.stderr}\n{res.stdout}"

    # Backup should be created and directory should exist
    expected_backup = backup_root / src.name
    backup_path = expected_backup.with_suffix(expected_backup.suffix + ".backup")
    assert backup_path.exists(), f"Expected backup in created directory: {backup_path}"
    assert backup_root.exists(), "Backup root directory should be created"


def test_cli_backup_root_with_skip_backup(tmp_path: Path):
    """Test that --backup-root is ignored when --skip-backup is used."""
    src = tmp_path / "test_cli_sample5.py"
    src.write_text(SAMPLE_SOURCE, encoding="utf-8")

    # Specify a backup root but also skip backups
    backup_root = tmp_path / "should_not_be_used"

    # Run CLI with both --backup-root and --skip-backup
    res = run_cli_migrate([str(src), "--backup-root", str(backup_root), "--skip-backup"])
    assert res.returncode == 0, f"CLI failed: {res.stderr}\n{res.stdout}"

    # No backup should be created anywhere since --skip-backup takes precedence
    backup_path = backup_root / src.name
    backup_path = backup_path.with_suffix(backup_path.suffix + ".backup")
    assert not backup_path.exists(), "Backup should not be created when --skip-backup is used"

    original_backup = src.with_suffix(src.suffix + ".backup")
    assert not original_backup.exists(), "Backup should not be created when --skip-backup is used"
