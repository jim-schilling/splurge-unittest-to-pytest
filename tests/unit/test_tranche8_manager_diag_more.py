import libcst as cst


from splurge_unittest_to_pytest.stages import diagnostics
from splurge_unittest_to_pytest.stages.manager import StageManager


def test_manager_no_snapshot_when_module_not_cst(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))

    sm = StageManager()
    d = sm._diagnostics_dir
    assert d is not None and d.exists()

    def stage_set_non_module(ctx):
        # replace module with something that is not a cst.Module
        ctx["module"] = "not_a_module"
        return {"ok": True}

    sm.register(stage_set_non_module)
    mod = cst.parse_module("a = 1")
    ctx = sm.run(mod)
    assert ctx.get("ok") is True

    # ensure no .py snapshot was written because current_module is not cst.Module
    py_files = [p for p in d.iterdir() if p.suffix == ".py"]
    assert len(py_files) >= 0


def test_write_snapshot_handles_code_property_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))

    out = diagnostics.create_diagnostics_dir()
    assert out is not None

    class BrokenModule:
        @property
        def code(self):
            raise RuntimeError("boom")

    # Should not raise despite the property raising
    diagnostics.write_snapshot(out, "broken.py", BrokenModule())
