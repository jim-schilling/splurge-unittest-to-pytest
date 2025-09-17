import os
from pathlib import Path


from splurge_unittest_to_pytest import print_diagnostics as pd

DOMAINS = ["core"]


def test_find_diagnostics_root_cli(tmp_path, monkeypatch):
    # When CLI root is provided, it should be honored
    cli = str(tmp_path / "cli-root")
    root = pd.find_diagnostics_root(cli)
    assert Path(cli) == root


def test_find_diagnostics_root_env(tmp_path, monkeypatch):
    # When env var is set and CLI not provided, env wins
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path / "env-root"))
    root = pd.find_diagnostics_root(None)
    assert Path(os.environ["SPLURGE_DIAGNOSTICS_ROOT"]) == root


def test_find_most_recent_run_empty(tmp_path):
    # No runs -> returns None
    assert pd.find_most_recent_run(tmp_path) is None


def test_find_most_recent_run_picks_latest(tmp_path):
    base = tmp_path
    d1 = base / "splurge-diagnostics-2025-01-01"
    d2 = base / "splurge-diagnostics-2025-02-02"
    d1.mkdir()
    d2.mkdir()
    # touch files to set mtime
    (d1 / "marker").write_text("one")
    (d2 / "marker").write_text("two")
    res = pd.find_most_recent_run(base)
    assert res is not None and res.name == d2.name


def test_print_run_info_and_main(tmp_path, capsys, monkeypatch):
    # Create a fake run dir with a marker file and some other files
    run = tmp_path / "splurge-diagnostics-2025-09-13"
    run.mkdir()
    (run / "splurge-diagnostics-001").write_text("marker-content")
    (run / "somefile.txt").write_text("hello")

    # Ensure find_most_recent_run will return our run when main is invoked
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))

    # Call main() which should print diagnostics info and return 0
    rv = pd.main([])
    assert rv == 0
    captured = capsys.readouterr()
    # Check that run path and marker contents are printed
    assert "Searching diagnostics root:" in captured.out
    assert "Diagnostics run directory:" in captured.out
    assert "marker-content" in captured.out
    assert "somefile.txt" in captured.out


def test_main_no_runs(tmp_path, capsys, monkeypatch):
    # No matching run directories under the root
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    rv = pd.main([])
    assert rv == 0
    captured = capsys.readouterr()
    assert "No diagnostics runs found under root." in captured.out


def test_print_run_info_marker_read_failure_and_no_marker(tmp_path, capsys, monkeypatch):
    run = tmp_path / "splurge-diagnostics-2025-09-13"
    run.mkdir()
    bad = run / "splurge-diagnostics-001"
    bad.write_text("marker-content")

    # Monkeypatch Path.read_text to raise for our bad marker, leave original for others
    orig_read = pd.Path.read_text

    def fake_read(self, encoding="utf-8"):
        if self == bad:
            raise OSError("boom")
        return orig_read(self, encoding=encoding)

    monkeypatch.setattr(pd.Path, "read_text", fake_read)

    # Should print marker name but report a failure to stderr
    pd.print_run_info(run)
    out_err = capsys.readouterr()
    assert "--- marker:" in out_err.out
    assert "Failed to read marker" in out_err.err

    # Now remove marker files to hit the 'no marker' path
    for p in list(run.iterdir()):
        p.unlink()
    pd.print_run_info(run)
    captured2 = capsys.readouterr()
    assert "No marker file found in run dir" in captured2.out
