import libcst as cst
from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.steps_assertion_rewriter import (
    TransformAlmostEqualAssertionsStep,
    TransformRegexAssertionsStep,
)


def test_run_steps_assertion_steps_set_import_flags():
    # Build a module containing an almost-equal assertion and a regex assertion
    src = """
class Test:
    def test_a(self):
        self.assertAlmostEqual(a, b)
        self.assertRegex(text, r"\\d+")
"""
    mod = cst.parse_module(src)
    context = {"module": mod}
    steps = [TransformAlmostEqualAssertionsStep(), TransformRegexAssertionsStep()]

    res = run_steps(
        stage_id="stages.assertion_rewriter",
        task_id="test.task",
        task_name="test",
        steps=steps,
        context=context,
        resources=None,
    )

    assert res.errors == []
    flags = res.delta.values
    # AlmostEqual should require pytest (approx), Regex should require re
    assert flags.get("needs_pytest_import") is True
    assert flags.get("needs_re_import") is True
