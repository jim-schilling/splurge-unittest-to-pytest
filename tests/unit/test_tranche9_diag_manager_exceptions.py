import tempfile
import libcst as cst

from pathlib import Path

import splurge_unittest_to_pytest.stages.diagnostics as diag
from splurge_unittest_to_pytest.stages.manager import StageManager


def test_create_diagnostics_mkdtemp_raises(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")

    # force tempfile.mkdtemp to raise
    def fake_mkdtemp(*a, **k):
        raise RuntimeError("mkdtemp failed")

    monkeypatch.setattr(tempfile, "mkdtemp", fake_mkdtemp)
    # should return None and not raise
    out = diag.create_diagnostics_dir()
    assert out is None


def test_create_diagnostics_marker_write_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))

    # make Path.write_text raise when called for the marker
    orig_write = Path.write_text

    def raise_on_write(self, *a, **k):
        raise OSError("nope")

    monkeypatch.setattr(Path, "write_text", raise_on_write)
    out = diag.create_diagnostics_dir()
    # when marker write fails, create_diagnostics_dir returns None
    assert out is None

    # restore not strictly necessary because monkeypatch will undo
    monkeypatch.setattr(Path, "write_text", orig_write)


def test_manager_handles_write_snapshot_exception(monkeypatch, tmp_path):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))

    # Create a StageManager (will create diagnostics dir)
    sm = StageManager()

    # monkeypatch diagnostics.write_snapshot to raise
    def raiser(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(diag, "write_snapshot", raiser)

    def stage(ctx):
        return {"x": 1}

    sm.register(stage)
    mod = cst.parse_module("a = 1")
    # should not raise despite write_snapshot raising inside register/run
    ctx = sm.run(mod)
    assert ctx.get("x") == 1
