from click.testing import CliRunner
import re
from splurge_unittest_to_pytest.cli import main as cli_main


def test_backup_hash_suffix_created(tmp_path, monkeypatch):
    f = tmp_path / "sample.py"
    content = "print('hello')\n"
    f.write_text(content)
    backup_dir = tmp_path / "bak"
    runner = CliRunner()

    # Run CLI (no conversion needed, but CLI will create backup)
    result = runner.invoke(cli_main, ["--backup", str(backup_dir), "--verbose", str(f)])
    assert result.exit_code == 0
    assert "Backup created" in result.output

    # Ensure backup dir exists and contains a file with .bak-<hex> suffix
    files = list(backup_dir.iterdir())
    assert files, "No files found in backup dir"
    pattern = re.compile(rf"^{re.escape(f.name)}\.bak-[0-9a-f]{{8}}$")
    matches = [p for p in files if pattern.match(p.name)]
    assert matches, f"No backup file matching pattern found in {backup_dir}: {files}"
