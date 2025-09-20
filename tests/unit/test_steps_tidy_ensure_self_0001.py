import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_tidy import EnsureSelfParamStep


def test_ensure_self_adds_self_to_methods():
    src = textwrap.dedent("""
    class TestThing:
        def test_method():
            assert True
    """)

    ctx = {"module": cst.parse_module(src)}
    resources = {}

    step = EnsureSelfParamStep()
    result = step.execute(ctx, resources)

    assert result.delta
    new_mod = result.delta.values.get("module")
    assert new_mod is not None
    out_src = new_mod.code
    # method should now include self in signature
    assert "def test_method(self)" in out_src
