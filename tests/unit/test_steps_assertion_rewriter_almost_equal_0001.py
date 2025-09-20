import libcst as cst
from splurge_unittest_to_pytest.stages.steps_assertion_rewriter import TransformAlmostEqualAssertionsStep


def _mod(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_almost_equal_step_sets_pytest_flag():
    src = "def test():\n    self.assertAlmostEqual(a, b)\n"
    step = TransformAlmostEqualAssertionsStep()
    res = step.execute({"module": _mod(src)}, resources=None)
    mod = res.delta.values.get("module")
    assert isinstance(mod, cst.Module)
    assert res.delta.values.get("needs_pytest_import", False) is True
