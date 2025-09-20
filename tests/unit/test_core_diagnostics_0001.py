"""Unit tests for splurge_unittest_to_pytest.print_diagnostics.

Focus on public behavior: root discovery, selecting the most recent run,
and printing run info. Tests avoid fragile exact output matches and use
monkeypatching only where necessary to simulate read failures.

This module-level docstring replaces a previous plain-text header which
caused import-time SyntaxError under pytest's assertion rewriting.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import libcst as cst

from splurge_unittest_to_pytest import print_diagnostics
from splurge_unittest_to_pytest import print_diagnostics as pd
from splurge_unittest_to_pytest.stages import generator_parts


def test_find_most_recent_run_empty(tmp_path):
    assert pd.find_most_recent_run(tmp_path) is None


def test_find_most_recent_run_picks_latest(tmp_path):
    base = tmp_path
    d1 = base / "splurge-diagnostics-2025-01-01"
    d2 = base / "splurge-diagnostics-2025-02-02"
    d1.mkdir()
    d2.mkdir()
    (d1 / "marker").write_text("one")
    (d2 / "marker").write_text("two")
    res = pd.find_most_recent_run(base)
    assert res is not None and res.name == d2.name


def test_print_run_info_and_main(tmp_path, capsys, monkeypatch):
    run = tmp_path / "splurge-diagnostics-2025-09-13"
    run.mkdir()
    (run / "splurge-diagnostics-001").write_text("marker-content")
    (run / "somefile.txt").write_text("hello")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    rv = pd.main(argv=[])
    assert rv == 0
    captured = capsys.readouterr()
    assert "Searching diagnostics root:" in captured.out
    assert "Diagnostics run directory:" in captured.out
    assert "marker-content" in captured.out
    assert "somefile.txt" in captured.out


def test_main_no_runs(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    rv = pd.main(argv=[])
    assert rv == 0
    captured = capsys.readouterr()
    assert "No diagnostics runs found under root." in captured.out


def test_print_run_info_marker_read_failure_and_no_marker(tmp_path, capsys, monkeypatch):
    run = tmp_path / "splurge-diagnostics-2025-09-13"
    run.mkdir()
    bad = run / "splurge-diagnostics-001"
    bad.write_text("marker-content")
    orig_read = pd.Path.read_text

    def fake_read(self, *, encoding="utf-8"):
        if self == bad:
            raise OSError("boom")
        return orig_read(self, encoding=encoding)

    monkeypatch.setattr(pd.Path, "read_text", fake_read)
    pd.print_run_info(run)
    out_err = capsys.readouterr()
    assert "--- marker:" in out_err.out
    assert "Failed to read marker" in out_err.err
    for p in list(run.iterdir()):
        p.unlink()
    pd.print_run_info(run)
    captured2 = capsys.readouterr()
    assert "No marker file found in run dir" in captured2.out


def test_node_emitter_emit_fixture_node_basic():
    emitter = generator_parts.node_emitter.NodeEmitter()
    fn = emitter.emit_fixture_node("my_fixture", "return 1")
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "my_fixture"
    assert any((isinstance(s, cst.SimpleStatementLine) for s in fn.body.body))


def test_node_emitter_emit_composite_dirs_node():
    emitter = generator_parts.node_emitter.NodeEmitter()
    mapping = {"a": "1", "b": "2"}
    fn = emitter.emit_composite_dirs_node("composite", mapping)
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "composite"
    src = cst.Module([]).code + "\n" + cst.Module([fn]).code
    assert "a" in src and "b" in src


def test_generator_core_make_fixture_basic():
    core = generator_parts.generator_core.GeneratorCore()
    fn = core.make_fixture("f1", "a = 1")
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "f1"


def test_print_diagnostics_find_and_print(tmp_path, capsys):
    root = tmp_path / "diagnostics_root"
    run = root / "splurge-diagnostics-0001"
    run.mkdir(parents=True)
    marker = run / "splurge-diagnostics-marker.txt"
    marker.write_text("marker")
    found = print_diagnostics.find_diagnostics_root(cli_root=str(root))
    assert found is not None
    recent = print_diagnostics.find_most_recent_run(found)
    assert recent is not None
    print_diagnostics.print_run_info(recent)
    captured = capsys.readouterr()
    assert "splurge-diagnostics-marker.txt" in captured.out or "marker" in captured.out


def test_find_diagnostics_root_cli_override(tmp_path):
    p = tmp_path / "my-root"
    p.mkdir()
    got = print_diagnostics.find_diagnostics_root(str(p))
    assert Path(got) == p


def test_find_diagnostics_root_env__01(monkeypatch, tmp_path):
    monkeypatch.delenv("SPLURGE_DIAGNOSTICS_ROOT", raising=False)
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    got = print_diagnostics.find_diagnostics_root(None)
    assert Path(got) == tmp_path


def test_find_diagnostics_root_default(monkeypatch, tmp_path):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    got = print_diagnostics.find_diagnostics_root(None)
    assert Path(got) == tmp_path


def test_find_most_recent_run_none_for_missing_root(tmp_path):
    missing = tmp_path / "does-not-exist"
    got = print_diagnostics.find_most_recent_run(missing)
    assert got is None


def test_find_most_recent_run_picks_latest__01(tmp_path):
    root = tmp_path / "diagroot"
    root.mkdir()
    a = root / "splurge-diagnostics-20250101"
    b = root / "splurge-diagnostics-20250201"
    a.mkdir()
    b.mkdir()
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
        assert "Failed to read marker" in err
    finally:
        monkeypatch.setattr(Path, "read_text", real_read_text)


def test_main_no_runs__01(tmp_path, capsys):
    rv = print_diagnostics.main(argv=["--root", str(tmp_path)])
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
    rv = print_diagnostics.main(argv=["--root", str(root)])
    out, err = capsys.readouterr()
    assert "Searching diagnostics root:" in out
    assert "Diagnostics run directory:" in out
    assert rv == 0
