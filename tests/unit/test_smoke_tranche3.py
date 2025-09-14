import libcst as cst

from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator
from splurge_unittest_to_pytest.converter.simple_fixture import create_simple_fixture
from splurge_unittest_to_pytest.stages.manager import StageManager


def test_build_pytest_fixture_decorator_various_values():
    # int value
    d_int = build_pytest_fixture_decorator({"count": 3})
    assert isinstance(d_int.decorator, cst.Call)
    kv = {arg.keyword.value: arg.value for arg in d_int.decorator.args}
    assert "count" in kv
    assert isinstance(kv["count"], cst.Integer)

    # None and False values
    d_none = build_pytest_fixture_decorator({"opt": None, "enabled": False})
    kv2 = {arg.keyword.value: arg.value for arg in d_none.decorator.args}
    assert isinstance(kv2["opt"], cst.Name)
    assert kv2["opt"].value == "None"
    assert isinstance(kv2["enabled"], cst.Name)
    assert kv2["enabled"].value == "False"

    # fallback object: uses Name(str(val))
    class X:
        def __str__(self):
            return "XOBJ"

    d_fb = build_pytest_fixture_decorator({"o": X()})
    kv3 = {arg.keyword.value: arg.value for arg in d_fb.decorator.args}
    assert isinstance(kv3["o"], cst.Name)


def test_create_simple_fixture_more_types():
    # float
    f1 = create_simple_fixture("f_float", cst.Float("1.5"))
    assert f1.returns.annotation.value == "float"

    # tuple, set, dict
    t = create_simple_fixture("f_tuple", cst.Tuple([]))
    assert t.returns.annotation.value == "Tuple"
    # cst.Set() requires at least one element; provide a single integer element
    s = create_simple_fixture("f_set", cst.Set([cst.Element(value=cst.Integer("1"))]))
    assert s.returns.annotation.value == "Set"
    d = create_simple_fixture("f_dict", cst.Dict([]))
    assert d.returns.annotation.value == "Dict"

    # None expression -> no return annotation
    n = create_simple_fixture("f_none", None)
    assert n.returns is None


def test_stage_manager_diagnostics_writes_snapshots(tmp_path, monkeypatch):
    # enable diagnostics and set root to tmp_path
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))

    mgr = StageManager()
    # after construction, diagnostics dir should be created when enabled
    assert mgr._diagnostics_dir is not None

    def flip_stage(ctx: dict):
        # return a new module to avoid mutating frozen libcst objects
        new_mod = cst.Module([cst.SimpleStatementLine(body=[cst.Expr(cst.Name("X"))])])
        return {"module": new_mod, "ok": True}

    mgr.register(flip_stage)
    mod = cst.Module([])
    out = mgr.run(mod)
    assert out.get("ok") is True

    # diagnostics dir should contain snapshot files
    files = list(mgr._diagnostics_dir.iterdir())
    assert files
