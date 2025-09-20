import libcst as cst

from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator
from splurge_unittest_to_pytest.converter.simple_fixture import create_simple_fixture
from splurge_unittest_to_pytest.stages import diagnostics
from splurge_unittest_to_pytest.stages.manager import StageManager


def test_stage_manager_register_and_run():
    mgr = StageManager()

    def sample_stage(ctx: dict):
        return {"collected": 1}

    mgr.register(sample_stage)
    mod = cst.Module([])
    out = mgr.run(mod, initial_context={"flag": True})
    assert out.get("collected") == 1
    assert isinstance(out.get("module"), cst.Module)
    mgr.dump_initial(mod)
    mgr.dump_final(mod)


def test_create_simple_fixture_annotations_and_body():
    int_expr = cst.Integer("1")
    fn = create_simple_fixture("f1", int_expr)
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "f1"
    stmt = fn.body.body[0]
    assert isinstance(stmt, cst.SimpleStatementLine)
    ret = stmt.body[0]
    assert isinstance(ret, cst.Return)
    assert isinstance(ret.value, cst.Integer)
    assert fn.returns is not None
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "int"
    sfn = create_simple_fixture("s1", cst.SimpleString("'x'"))
    assert sfn.returns.annotation.value == "str"
    lfn = create_simple_fixture("l1", cst.List([]))
    assert lfn.returns.annotation.value == "List"


def test_build_pytest_fixture_decorator_no_kwargs_and_with_kwargs():
    d = build_pytest_fixture_decorator(None)
    assert isinstance(d, cst.Decorator)
    assert isinstance(d.decorator, cst.Attribute)
    assert d.decorator.attr.value == "fixture"
    d2 = build_pytest_fixture_decorator({"autouse": True, "scope": "module"})
    assert isinstance(d2.decorator, cst.Call)
    kws = [arg.keyword.value for arg in d2.decorator.args if arg.keyword is not None]
    assert kws == ["autouse", "scope"]


def test_diagnostics_flags_and_snapshot(tmp_path, monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    assert diagnostics.diagnostics_enabled() is False
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    assert diagnostics.diagnostics_enabled() is True
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    out = diagnostics.create_diagnostics_dir()
    assert out is not None
    markers = list(out.glob("splurge-diagnostics-*"))
    assert markers

    class M:
        code = "x=1\n"

    diagnostics.write_snapshot(tmp_path, "file.py", M)
    p = tmp_path / "file.py"
    assert p.exists()
    assert p.read_text(encoding="utf-8") == "x=1\n"
