import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.annotation_inferer import AnnotationInferer
from splurge_unittest_to_pytest.converter.call_utils import is_self_call
from splurge_unittest_to_pytest.stages.manager import StageManager
from splurge_unittest_to_pytest.stages import diagnostics

DOMAINS = ["converter", "generator", "helpers", "literals", "manager", "stages", "transform"]


def test_annotation_inferer():
    ai = AnnotationInferer()
    assert ai.infer_return_annotation("test_foo") == "-> Any"
    assert ai.infer_return_annotation("foo") == "-> None"


def test_is_self_call_true_false():
    # self.method(1, 'x') -> should be recognized
    call = cst.parse_expression("self.method(1, 'x')")
    res = is_self_call(call)
    assert res is not None
    name, args = res
    assert name == "method"
    assert len(args) == 2

    # non-self call should return None
    call2 = cst.parse_expression("other.method(1)")
    assert is_self_call(call2) is None


def test_stage_manager_register_and_run_no_diagnostics(monkeypatch):
    # ensure diagnostics disabled for this run
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    sm = StageManager()

    def stage_add(context):
        # return a dict to be merged into context
        return {"added": 1}

    sm.register(stage_add)
    mod = cst.parse_module("x = 1")
    ctx = sm.run(mod)
    assert ctx["module"] is mod
    assert ctx["added"] == 1


def test_diagnostics_create_and_write(tmp_path, monkeypatch):
    # Enable diagnostics and point to tmp_path
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))

    out = diagnostics.create_diagnostics_dir()
    assert out is not None and out.exists()

    class DummyModule:
        code = "print('hello')"

    diagnostics.write_snapshot(out, "snap.py", DummyModule())
    p = out / "snap.py"
    assert p.exists()

    # write_snapshot should no-op gracefully when out_dir is None
    diagnostics.write_snapshot(None, "snap2.py", DummyModule())
