import libcst as cst

from splurge_unittest_to_pytest.stages import diagnostics
from splurge_unittest_to_pytest.stages.manager import StageManager


def test_diagnostics_flag_variants(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    assert diagnostics.diagnostics_enabled() is True

    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "0")
    assert diagnostics.diagnostics_enabled() is False

    # verbose flag
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_VERBOSE", "1")
    assert diagnostics.diagnostics_verbose() is True
    monkeypatch.delenv("SPLURGE_DIAGNOSTICS_VERBOSE", raising=False)


def test_write_snapshot_defensive(tmp_path):
    class Dummy:
        code = "print('x')"

    # out_dir is not a Path -> should no-op and not raise
    diagnostics.write_snapshot("not_a_path", "f.py", Dummy())

    # out_dir is None -> no-op
    diagnostics.write_snapshot(None, "f2.py", Dummy())


def test_stage_manager_callable_object_without_name(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))

    sm = StageManager()
    d = sm._diagnostics_dir
    assert d is not None and d.exists()

    class CallableObj:
        def __call__(self, ctx):
            return {"ok": True}

    obj = CallableObj()
    sm.register(obj)
    mod = cst.parse_module("y = 2")
    ctx = sm.run(mod)
    assert ctx.get("ok") is True

    # diagnostics files should include snapshots (py files) or marker
    names = [p.name for p in d.iterdir()]
    assert any(n.endswith(".py") or n.startswith("splurge-diagnostics-") for n in names)


def test_dump_noop_when_diagnostics_disabled(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    sm = StageManager()
    # should not raise even when diagnostics disabled
    mod = cst.parse_module("z = 3")
    sm.dump_initial(mod)
    sm.dump_final(mod)
