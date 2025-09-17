import os
from pathlib import Path

import libcst as cst

from splurge_unittest_to_pytest.stages import diagnostics

DOMAINS = ["core"]


def test_write_snapshot_logs_on_failure(monkeypatch, caplog, tmp_path: Path) -> None:
    os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = "1"
    try:
        caplog.set_level("ERROR", logger="splurge.diagnostics")
        d = diagnostics.create_diagnostics_dir()
        assert d is not None

        # Monkeypatch Path.write_text to raise an exception to simulate write failure
        original_write_text = Path.write_text

        def fail_write(self, *args, **kwargs):
            raise IOError("disk full")

        monkeypatch.setattr(Path, "write_text", fail_write)

        # Attempt to write snapshot; should not raise but should log an error
        diagnostics.write_snapshot(d, "bad_snapshot.py", cst.parse_module("x = 1"))

        assert any("splurge.diagnostics" in r.name or r.name == "splurge.diagnostics" for r in caplog.records)
        assert any(
            "write_snapshot failed" in r.getMessage() or "failed to write" in r.getMessage() for r in caplog.records
        )
    finally:
        os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)
        # restore write_text to be safe
        try:
            monkeypatch.setattr(Path, "write_text", original_write_text)
        except Exception:
            pass
