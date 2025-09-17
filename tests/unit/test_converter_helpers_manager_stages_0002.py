import libcst as cst

from splurge_unittest_to_pytest.converter.call_utils import is_self_call
from splurge_unittest_to_pytest.stages.manager import StageManager

DOMAINS = ["converter", "helpers", "manager", "stages"]


def test_stage_returns_none_and_mutates_context(monkeypatch):
    # diagnostics off
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    sm = StageManager()

    def mut_stage(ctx):
        # mutate context in-place and return None
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
    # non-dict return should not be merged; module still present
    assert out.get("module") is not None


def test_is_self_call_nested_attribute():
    # call like obj.attr.method() -> top-level call.func is Attribute but
    # func.value is also Attribute (not Name), so should return None.
    call = cst.parse_expression("obj.attr.method()")
    assert is_self_call(call) is None
