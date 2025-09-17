import libcst as cst
from splurge_unittest_to_pytest.converter.call_utils import is_self_call
from splurge_unittest_to_pytest.stages.manager import StageManager


def test_is_self_call_exception_path():
    assert is_self_call(None) is None


def test_stage_manager_diagnostics_snapshots(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    sm = StageManager()
    d = sm._diagnostics_dir
    assert d is not None and d.exists()

    def sample_stage(ctx):
        return {"stage_marker": True}

    sm.register(sample_stage)
    mod = cst.parse_module("a = 1")
    ctx = sm.run(mod)
    assert ctx.get("stage_marker") is True
    sm.dump_initial(mod)
    sm.dump_final(mod)
    files = list(d.iterdir())
    assert any((p.suffix == "" or p.name.startswith("splurge-diagnostics-") or p.name.endswith(".py") for p in files))


def test_stage_returns_none_and_mutates_context(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    sm = StageManager()

    def mut_stage(ctx):
        ctx["mutated"] = "yes"
        return None

    sm.register(mut_stage)
    mod = cst.parse_module("a = 1")
    out = sm.run(mod)
    assert out.get("mutated") == "yes"


def test_stage_returns_non_dict(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    sm = StageManager()

    def weird_stage(ctx):
        return [1, 2, 3]

    sm.register(weird_stage)
    mod = cst.parse_module("b = 2")
    out = sm.run(mod)
    assert out.get("module") is not None


def test_is_self_call_nested_attribute():
    call = cst.parse_expression("obj.attr.method()")
    assert is_self_call(call) is None
