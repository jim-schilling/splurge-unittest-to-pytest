import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.steps_rewriter import RewriteMethodParamsStep


def test_rewriter_step_integration_basic():
    src = textwrap.dedent("""
    class TestA:
        def test_x():
            pass
    """)

    context = {
        "module": cst.parse_module(src),
        "collector_output": type("C", (), {"classes": {}})(),
        "__stage_id__": "stages.rewriter",
    }
    steps = [RewriteMethodParamsStep()]
    result = run_steps(
        "stages.rewriter", "tasks.rewriter.rewrite_method_params", "rewrite_method_params", steps, context, {}
    )
    assert result.delta.values.get("module") is not None
    assert "def test_x(self)" in result.delta.values.get("module").code
