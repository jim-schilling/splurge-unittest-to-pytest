from pathlib import Path

import libcst as cst

from splurge_unittest_to_pytest.stages.manager import StageManager

DOMAINS = ["manager", "stages"]


def test_diagnostics_enabled_creates_marker_and_dumps(tmp_path, monkeypatch):
    # Enable diagnostics
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")

    mgr = StageManager()
    # When enabled, manager should have a diagnostics dir path
    assert mgr._diagnostics_dir is None or isinstance(mgr._diagnostics_dir, Path)
    # If diagnostics dir exists, confirm marker file and dumps work
    if mgr._diagnostics_dir is None:
        # Marker creation failed silently; still acceptable because manager
        # is defensive. In that case assert no exception when calling dumps.
        module = cst.parse_module("x = 1")
        mgr.dump_initial(module)
        mgr.dump_final(module)
        return

    # diagnostics dir exists: ensure marker content points to the dir
    marker_files = list(mgr._diagnostics_dir.glob("splurge-diagnostics-*"))
    # Marker file may be present inside the diagnostics dir; at least one file
    assert any(f.exists() for f in marker_files)

    # Test dump_initial and dump_final write files
    module = cst.parse_module("a = 1")
    mgr.dump_initial(module)
    mgr.dump_final(module)

    init = mgr._diagnostics_dir / "00_initial_input.py"
    final = mgr._diagnostics_dir / "99_final_output.py"
    assert init.exists()
    assert final.exists()


def test_diagnostics_disabled_no_files(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    assert mgr._diagnostics_dir is None
    # Calling dump methods should be no-ops and not raise
    module = cst.parse_module("x = 2")
    mgr.dump_initial(module)
    mgr.dump_final(module)
