import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import AssertionRewriter
from splurge_unittest_to_pytest.stages.steps_assertion_rewriter import (
    TransformComparisonAssertionsStep,
    TransformRaisesAssertionsStep,
)


def _module(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_transform_comparison_step_parity():
    src = """
def test_example():
    self.assertEqual(1, 1)
"""
    mod = _module(src)

    # Baseline using the transformer directly
    transformer = AssertionRewriter()
    mod_direct = mod.visit(transformer)

    # Run using the Step
    step = TransformComparisonAssertionsStep()

    res = step.execute({"module": mod}, resources=None)
    mod_step = res.delta.values.get("module")

    assert isinstance(mod_direct, cst.Module)
    assert isinstance(mod_step, cst.Module)
    assert mod_direct.code == mod_step.code


def test_transform_raises_step_noop_preserves_module():
    src = """
def test_example():
    with self.assertRaises(ValueError):
        raise ValueError()
"""
    mod = _module(src)
    step = TransformRaisesAssertionsStep()
    res = step.execute({"module": mod}, resources=None)
    mod_after = res.delta.values.get("module")

    # The placeholder raises step is currently a no-op; ensure module preserved
    assert isinstance(mod_after, cst.Module)
    assert mod_after.code == mod.code
