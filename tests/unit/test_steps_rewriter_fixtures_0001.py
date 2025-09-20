import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_rewriter import RewriteMethodParamsStep


def test_adds_fixture_params_from_collector():
    src = textwrap.dedent("""
    class TestZ:
        def test_has_fixtures(self):
            pass
    """)

    mod = cst.parse_module(src)
    class_info = type("CI", (), {"setup_assignments": {"fx1": None, "fx2": None}})()
    collector = type("C", (), {"classes": {"TestZ": class_info}})()
    res = RewriteMethodParamsStep().execute({"module": mod, "collector_output": collector}, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    # fx1 and fx2 should be present as params
    assert "fx1" in new_mod.code and "fx2" in new_mod.code
