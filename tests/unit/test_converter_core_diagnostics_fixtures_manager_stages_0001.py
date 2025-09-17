import libcst as cst

from splurge_unittest_to_pytest.stages.manager import StageManager
from splurge_unittest_to_pytest.converter.simple_fixture import create_simple_fixture
from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator
from splurge_unittest_to_pytest.stages import diagnostics

DOMAINS = ["converter", "fixtures", "manager", "stages"]


def test_stage_manager_register_and_run():
    mgr = StageManager()

    def sample_stage(ctx: dict):
        # stage returns a small dict result; manager should merge it
        return {"collected": 1}

    mgr.register(sample_stage)
    mod = cst.Module([])
    out = mgr.run(mod, initial_context={"flag": True})
    assert out.get("collected") == 1
    assert isinstance(out.get("module"), cst.Module)

    # dump helpers are defensive; calling them should not raise
    mgr.dump_initial(mod)
    mgr.dump_final(mod)


def test_create_simple_fixture_annotations_and_body():
    int_expr = cst.Integer("1")
    fn = create_simple_fixture("f1", int_expr)
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "f1"
    # body contains a single return statement with our integer
    stmt = fn.body.body[0]
    assert isinstance(stmt, cst.SimpleStatementLine)
    ret = stmt.body[0]
    assert isinstance(ret, cst.Return)
    assert isinstance(ret.value, cst.Integer)
    # return annotation inferred to 'int'
    assert fn.returns is not None
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "int"

    # string and list annotations
    sfn = create_simple_fixture("s1", cst.SimpleString("'x'"))
    assert sfn.returns.annotation.value == "str"
    lfn = create_simple_fixture("l1", cst.List([]))
    assert lfn.returns.annotation.value == "List"


def test_build_pytest_fixture_decorator_no_kwargs_and_with_kwargs():
    d = build_pytest_fixture_decorator(None)
    assert isinstance(d, cst.Decorator)
    # no-kwargs form should be an attribute reference `pytest.fixture`
    assert isinstance(d.decorator, cst.Attribute)
    assert d.decorator.attr.value == "fixture"

    d2 = build_pytest_fixture_decorator({"autouse": True, "scope": "module"})
    assert isinstance(d2.decorator, cst.Call)
    # args are emitted in deterministic sorted order
    kws = [arg.keyword.value for arg in d2.decorator.args if arg.keyword is not None]
    assert kws == ["autouse", "scope"]


def test_diagnostics_flags_and_snapshot(tmp_path, monkeypatch):
    # By default diagnostics should be disabled
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    assert diagnostics.diagnostics_enabled() is False
    # enabling diagnostics flips the flag
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    assert diagnostics.diagnostics_enabled() is True

    # create_diagnostics_dir should respect a custom root; use tmp_path
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    out = diagnostics.create_diagnostics_dir()
    assert out is not None
    # marker file should be present in the created directory
    markers = list(out.glob("splurge-diagnostics-*"))
    assert markers

    # write_snapshot should write module.code when given a Path
    class M:
        code = "x=1\n"

    diagnostics.write_snapshot(tmp_path, "file.py", M)
    p = tmp_path / "file.py"
    assert p.exists()
    assert p.read_text(encoding="utf-8") == "x=1\n"
