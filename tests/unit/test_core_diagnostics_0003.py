"""Unit tests for splurge_unittest_to_pytest.print_diagnostics.

Focus on public behavior: root discovery, selecting the most recent run,
and printing run info. Tests avoid fragile exact output matches and use
monkeypatching only where necessary to simulate read failures.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
import tempfile


from splurge_unittest_to_pytest import print_diagnostics


def test_find_diagnostics_root_cli_override(tmp_path):
    p = tmp_path / "my-root"
    p.mkdir()
    got = print_diagnostics.find_diagnostics_root(str(p))
    assert Path(got) == p


def test_find_diagnostics_root_env(monkeypatch, tmp_path):
    monkeypatch.delenv("SPLURGE_DIAGNOSTICS_ROOT", raising=False)
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    got = print_diagnostics.find_diagnostics_root(None)
    assert Path(got) == tmp_path


def test_find_diagnostics_root_default(monkeypatch, tmp_path):
    # Force tempfile.gettempdir() to a known value (use tmp_path to avoid OS
    # differences and recursion into tempfile.gettempdir())
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    got = print_diagnostics.find_diagnostics_root(None)
    assert Path(got) == tmp_path


def test_find_most_recent_run_none_for_missing_root(tmp_path):
    missing = tmp_path / "does-not-exist"
    got = print_diagnostics.find_most_recent_run(missing)
    assert got is None


def test_find_most_recent_run_picks_latest(tmp_path):
    root = tmp_path / "diagroot"
    root.mkdir()
    a = root / "splurge-diagnostics-20250101"
    b = root / "splurge-diagnostics-20250201"
    a.mkdir()
    b.mkdir()

    # set mtimes: make b newer
    now = time.time()
    os.utime(a, (now - 1000, now - 1000))
    os.utime(b, (now, now))

    got = print_diagnostics.find_most_recent_run(root)
    assert got is not None
    assert Path(got).name == b.name


def test_print_run_info_with_markers_and_files(tmp_path, capsys):
    run = tmp_path / "splurge-diagnostics-202501"
    run.mkdir()
    marker = run / "splurge-diagnostics-foo"
    marker.write_text("marker-contents", encoding="utf-8")
    (run / "somefile.txt").write_text("hello")

    print_diagnostics.print_run_info(run)
    out, err = capsys.readouterr()

    assert "Diagnostics run directory:" in out
    assert "--- marker: splurge-diagnostics-foo" in out
    assert "marker-contents" in out
    assert "Files in diagnostics run:" in out
    assert "somefile.txt" in out
    assert err == ""


def test_print_run_info_handles_read_error(tmp_path, capsys, monkeypatch):
    run = tmp_path / "splurge-diagnostics-202502"
    run.mkdir()
    marker = run / "splurge-diagnostics-bad"
    marker.write_text("secret", encoding="utf-8")

    # Monkeypatch Path.read_text to raise for this particular marker
    real_read_text = Path.read_text

    def fake_read_text(self, *args, **kwargs):
        if self == marker:
            raise OSError("read failed")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    try:
        print_diagnostics.print_run_info(run)
        out, err = capsys.readouterr()

        assert "Diagnostics run directory:" in out
        # When read_text fails, error message should be printed to stderr
        assert "Failed to read marker" in err
    finally:
        monkeypatch.setattr(Path, "read_text", real_read_text)


def test_main_no_runs(tmp_path, capsys):
    # main should handle empty root gracefully and return 0
    rv = print_diagnostics.main(["--root", str(tmp_path)])
    out, err = capsys.readouterr()
    assert "Searching diagnostics root:" in out
    assert "No diagnostics runs found under root." in out
    assert rv == 0


def test_main_finds_and_prints_run(tmp_path, capsys):
    root = tmp_path / "root"
    root.mkdir()
    run = root / "splurge-diagnostics-1"
    run.mkdir()
    (run / "splurge-diagnostics-mark").write_text("ok")

    rv = print_diagnostics.main(["--root", str(root)])
    out, err = capsys.readouterr()
    assert "Searching diagnostics root:" in out
    assert "Diagnostics run directory:" in out
    assert rv == 0
