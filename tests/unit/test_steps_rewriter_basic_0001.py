import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_rewriter import RewriteMethodParamsStep


def test_adds_self_when_missing():
    src = textwrap.dedent("""
    class TestX:
        def test_one():
            assert True
    """)

    mod = cst.parse_module(src)
    collector = type("C", (), {"classes": {}})()
    res = RewriteMethodParamsStep().execute({"module": mod, "collector_output": collector}, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    assert "def test_one(self)" in new_mod.code
