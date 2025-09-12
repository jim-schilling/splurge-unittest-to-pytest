import os
from pathlib import Path

import libcst as cst
from splurge_unittest_to_pytest.stages import diagnostics


def test_diagnostics_disabled_by_default(tmp_path: Path) -> None:
    # Ensure env var is unset
    os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)
    out = diagnostics.create_diagnostics_dir()
    assert out is None


def test_diagnostics_create_and_write_snapshot(tmp_path: Path) -> None:
    # Enable diagnostics for this test
    os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = "1"
    out = diagnostics.create_diagnostics_dir()
    try:
        assert out is not None
        # create a tiny module object with `code` attribute
        module = cst.parse_module("x = 1")
        diagnostics.write_snapshot(out, "test_snapshot.py", module)
        p = out / "test_snapshot.py"
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "x = 1" in content
    finally:
        # cleanup env var and temp dir
        os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)
        try:
            # best-effort cleanup
            for f in out.iterdir():
                f.unlink()
            out.rmdir()
        except Exception:
            pass
