import libcst as cst
from splurge_unittest_to_pytest.stages.steps_assertion_rewriter import TransformTruthinessAssertionsStep


def _mod(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_truthiness_step_converts_assert_true_and_false():
    src = "def test():\n    self.assertTrue(x, 'msg')\n    self.assertFalse(y, 'msg2')\n"
    step = TransformTruthinessAssertionsStep()
    res = step.execute({"module": _mod(src)}, resources=None)
    mod = res.delta.values.get("module")
    assert isinstance(mod, cst.Module)
    code = mod.code
    # transformer currently drops optional 'msg' arguments and emits simple asserts
    assert "assert x" in code
    assert "assert not y" in code
