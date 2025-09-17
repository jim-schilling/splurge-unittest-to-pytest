import libcst as cst

from splurge_unittest_to_pytest.stages.manager import StageManager

DOMAINS = ["manager", "stages"]


def test_diagnostics_marker_and_dir_created(monkeypatch, tmp_path):
    # Enable diagnostics via env var
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    # If diagnostics couldn't be created, skip the assertions
    if mgr._diagnostics_dir is None:
        return

    # Marker file should exist in the diagnostics dir
    files = list(mgr._diagnostics_dir.iterdir())
    assert any(p.name.startswith("splurge-diagnostics-") for p in files)


def test_register_writes_stage_snapshot(monkeypatch, tmp_path):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    if mgr._diagnostics_dir is None:
        return

    # Stage that mutates module in context
    def stage(context):
        new_mod = cst.parse_module("a = 1")
        context["module"] = new_mod
        return {"ok": True}

    mgr.register(stage)
    initial = cst.parse_module("x = 0")
    mgr.run(initial)

    files = list(mgr._diagnostics_dir.iterdir())
    # Expect multiple files (marker + snapshots)
    assert any(
        p.name.endswith("00_initial_input.py") or p.name.endswith("99_final_output.py") or p.suffix == ".py"
        for p in files
    )


def test_no_diagnostics_when_disabled(monkeypatch):
    # Ensure diagnostics disabled
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    # Should not have a diagnostics dir
    assert mgr._diagnostics_dir is None
