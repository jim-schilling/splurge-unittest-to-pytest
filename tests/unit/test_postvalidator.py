import libcst as cst
from splurge_unittest_to_pytest.stages.postvalidator import postvalidator_stage


def test_postvalidator_accepts_valid_module():
    src = 'import pytest\n\nclass A:\n    pass\n'
    module = cst.parse_module(src)
    res = postvalidator_stage({"module": module})
    assert "postvalidator_error" not in res


def test_postvalidator_detects_syntax_error():
    # craft a module that becomes invalid when string is replaced (simulate bad transform)
    src = 'def f():\n    return 1\n'
    module = cst.parse_module(src)
    # monkey-patch module.code to return invalid code
    class M:
        code = "def f(:\n"
    res = postvalidator_stage({"module": M()})
    assert "postvalidator_error" in res
