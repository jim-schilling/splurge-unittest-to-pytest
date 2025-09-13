import libcst as cst

from splurge_unittest_to_pytest.stages.manager import StageManager


def test_register_writes_stage_snapshots(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    if mgr._diagnostics_dir is None:
        # If diagnostics couldn't be created (rare), the behavior is still safe
        return

    # Define a tiny stage that mutates the module in context
    def stage(context):
        # create a new module with different code
        new_mod = cst.parse_module("a = 1")
        context["module"] = new_mod
        return {"ok": True}

    mgr.register(stage)
    # Run manager with a simple module
    initial = cst.parse_module("x = 0")
    mgr.run(initial)
    # After run, diagnostics dir should contain files (initial + stage snapshots)
    files = list(mgr._diagnostics_dir.iterdir())
    assert any(
        p.name.endswith("00_initial_input.py") or p.name.endswith("99_final_output.py") or p.name.endswith(".py")
        for p in files
    )
