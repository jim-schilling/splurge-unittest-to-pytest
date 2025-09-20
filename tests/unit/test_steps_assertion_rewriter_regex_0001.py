import libcst as cst

from splurge_unittest_to_pytest.stages.steps_assertion_rewriter import TransformRegexAssertionsStep


def _mod(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_regex_step_sets_re_flag_and_search():
    src = "def test():\n    self.assertRegex(text, pattern)\n"
    step = TransformRegexAssertionsStep()
    res = step.execute({"module": _mod(src)}, resources=None)
    mod = res.delta.values.get("module")
    assert isinstance(mod, cst.Module)
    assert res.delta.values.get("needs_re_import", False) is True
    # ensure re.search exists somewhere in the module
    code = mod.code
    assert "re.search" in code
