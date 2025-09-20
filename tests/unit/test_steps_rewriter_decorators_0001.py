import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_rewriter import RewriteMethodParamsStep


def test_classmethod_preserves_cls_and_static_untouched():
    src = textwrap.dedent("""
    class TestY:
        @classmethod
        def test_cls():
            pass

        @staticmethod
        def test_static():
            pass
    """)

    mod = cst.parse_module(src)
    collector = type("C", (), {"classes": {}})()
    res = RewriteMethodParamsStep().execute({"module": mod, "collector_output": collector}, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    assert "def test_cls(cls)" in new_mod.code
    # staticmethod should remain without self/cls
    assert "def test_static()" in new_mod.code
