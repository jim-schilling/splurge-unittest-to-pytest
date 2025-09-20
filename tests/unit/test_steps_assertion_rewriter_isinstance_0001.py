import libcst as cst

from splurge_unittest_to_pytest.stages.steps_assertion_rewriter import TransformIsInstanceAssertionsStep


def _mod(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_isinstance_step_converts_assert_isinstance():
    src = "def test():\n    self.assertIsInstance(obj, MyClass, 'msg')\n"
    step = TransformIsInstanceAssertionsStep()
    res = step.execute({"module": _mod(src)}, resources=None)
    mod = res.delta.values.get("module")
    assert isinstance(mod, cst.Module)
    code = mod.code
    # transformer drops optional message arg; we expect an isinstance check
    assert "assert isinstance(obj, MyClass" in code
