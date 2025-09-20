import os
from pathlib import Path

import libcst as cst

from splurge_unittest_to_pytest.stages import diagnostics


def test_diagnostics_disabled_by_default(tmp_path: Path) -> None:
    os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)
    out = diagnostics.create_diagnostics_dir()
    assert out is None


def test_diagnostics_create_and_write_snapshot(tmp_path: Path) -> None:
    os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = "1"
    out = diagnostics.create_diagnostics_dir()
    try:
        assert out is not None
        module = cst.parse_module("x = 1")
        diagnostics.write_snapshot(out, "test_snapshot.py", module)
        p = out / "test_snapshot.py"
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "x = 1" in content
    finally:
        os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)
        try:
            for f in out.iterdir():
                f.unlink()
            out.rmdir()
        except Exception:
            pass


def test_write_snapshot_logs_on_failure(monkeypatch, caplog, tmp_path: Path) -> None:
    os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = "1"
    try:
        caplog.set_level("ERROR", logger="splurge.diagnostics")
        d = diagnostics.create_diagnostics_dir()
        assert d is not None
        original_write_text = Path.write_text

        def fail_write(self, *args, **kwargs):
            raise IOError("disk full")

        monkeypatch.setattr(Path, "write_text", fail_write)
        diagnostics.write_snapshot(d, "bad_snapshot.py", cst.parse_module("x = 1"))
        assert any(("splurge.diagnostics" in r.name or r.name == "splurge.diagnostics" for r in caplog.records))
        assert any(
            ("write_snapshot failed" in r.getMessage() or "failed to write" in r.getMessage() for r in caplog.records)
        )
    finally:
        os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)
        try:
            monkeypatch.setattr(Path, "write_text", original_write_text)
        except Exception:
            pass


def test_diagnostics_root_override(tmp_path: Path) -> None:
    os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = "1"
    try:
        os.environ["SPLURGE_DIAGNOSTICS_ROOT"] = str(tmp_path)
        out = diagnostics.create_diagnostics_dir()
        assert out is not None
        assert tmp_path in out.parents or out == tmp_path
    finally:
        os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)
        os.environ.pop("SPLURGE_DIAGNOSTICS_ROOT", None)
