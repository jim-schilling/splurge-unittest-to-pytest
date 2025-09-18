from click.testing import CliRunner
from pathlib import Path
import os
from splurge_unittest_to_pytest.cli import main as cli_main


def test_backup_root_path_warns(tmp_path):
    # emulate a root path by using the drive root on Windows or '/' on POSIX
    if os.name == "nt":
        root = Path(tmp_path.drive + "\\")
    else:
        root = Path("/")

    f = tmp_path / "sample2.py"
    f.write_text("print(2)\n")
    runner = CliRunner()
    # Running CLI with backup root should produce a warning and not attempt to create backups
    result = runner.invoke(cli_main, ["--backup", str(root), "--verbose", str(f)])
    # We expect either a warning message or non-zero exit due to invalid backup directory handling
    assert result.exit_code in (0, 1)
    assert ("backup directory appears to be root" in result.output) or ("Warning:" in result.output)


def test_backup_resolve_failure_handles_exception(tmp_path, monkeypatch):
    f = tmp_path / "sample3.py"
    f.write_text("print(3)\n")
    backup_dir = tmp_path / "bak"

    # Monkeypatch Path.resolve to raise when called to simulate failure
    orig_resolve = Path.resolve

    def fake_resolve(self):
        raise OSError("resolve failed")

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    runner = CliRunner()
    result = runner.invoke(cli_main, ["--backup", str(backup_dir), "--verbose", str(f)])

    # Restore original resolve to avoid side-effects for other tests
    monkeypatch.setattr(Path, "resolve", orig_resolve)

    assert result.exit_code in (0, 1)
    # Should have either created the backup dir or printed a warning about failure
    assert (
        ("Warning: Failed to create backup" in result.output)
        or ("Warning:" in result.output)
        or ("Backup created" in result.output)
    )
