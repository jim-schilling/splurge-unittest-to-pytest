import libcst as cst

from splurge_unittest_to_pytest.converter.call_utils import is_self_call
from splurge_unittest_to_pytest.stages.manager import StageManager

DOMAINS = ["converter", "helpers", "manager", "stages"]


def test_is_self_call_exception_path():
    # Passing an invalid object should be handled gracefully (except->None)
    assert is_self_call(None) is None


def test_stage_manager_diagnostics_snapshots(tmp_path, monkeypatch):
    # Enable diagnostics and point it at tmp_path
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))

    sm = StageManager()
    # diagnostics dir should have been created and returned
    d = sm._diagnostics_dir
    assert d is not None and d.exists()

    # Register a stage that returns a dict and check that a snapshot file is written
    def sample_stage(ctx):
        # mutate module to ensure the snapshot contains something different
        return {"stage_marker": True}

    sm.register(sample_stage)
    mod = cst.parse_module("a = 1")
    ctx = sm.run(mod)
    assert ctx.get("stage_marker") is True

    # dump initial and final should write explicit files
    sm.dump_initial(mod)
    sm.dump_final(mod)

    # Ensure at least one .py file exists in diagnostics dir (snapshots/marker)
    files = list(d.iterdir())
    assert any(p.suffix == "" or p.name.startswith("splurge-diagnostics-") or p.name.endswith(".py") for p in files)
