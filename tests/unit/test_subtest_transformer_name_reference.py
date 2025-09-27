import libcst as cst

from splurge_unittest_to_pytest.transformers.subtest_transformer import (
    convert_simple_subtests_to_parametrize,
)


class DummyTransformer:
    def __init__(self):
        self.needs_pytest_import = False


def _get_function(code: str) -> cst.FunctionDef:
    module = cst.parse_module(code)
    # assume single function at top-level
    for node in module.body:
        if isinstance(node, cst.FunctionDef):
            return node
    raise AssertionError("No function found in code")


def test_convert_using_name_reference_to_prior_assignment():
    code = """
def test_examples():
    vals = [1, 2, 3]
    for v in vals:
        with self.subTest(v):
            assert True
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is not None
    # should have added a decorator
    decs = list(res.decorators or [])
    assert len(decs) >= 1
    # first decorator should be pytest.mark.parametrize("v", [1,2,3])
    first = decs[0].decorator
    assert isinstance(first, cst.Call)
    # basic textual checks
    s = cst.Module([res]).code
    assert "parametrize" in s
    assert "pytest" in s
    assert transformer.needs_pytest_import is True


def test_convert_using_name_reference_missing_assignment():
    code = """
def test_examples():
    for v in vals:
        with self.subTest(v):
            assert True
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is None
