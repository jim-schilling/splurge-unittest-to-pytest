import libcst as cst

from splurge_unittest_to_pytest.transformers.parametrize_helper import (
    ParametrizeConversionError,
    convert_subtest_loop_to_parametrize,
)


class DummyTransformer:
    def __init__(self) -> None:
        self.needs_pytest_import = False
        self.parametrize_include_ids = True
        self.parametrize_add_annotations = False


def _parse_function(code: str) -> cst.FunctionDef:
    module = cst.parse_module(code)
    # Expect single function def at module level
    for stmt in module.body:
        if isinstance(stmt, cst.FunctionDef):
            return stmt
    raise AssertionError("no function found in code")


def test_convert_simple_subtest_loop_adds_parametrize():
    code = """
def test_example(self):
    sizes = [1, 2]
    for s in sizes:
        with self.subTest(s=s):
            assert s > 0
"""

    func = _parse_function(code)
    updated = func
    transformer = DummyTransformer()

    result = convert_subtest_loop_to_parametrize(func, updated, transformer)
    assert result is not None
    assert transformer.needs_pytest_import is True
    # The top decorator should be a parametrize call
    assert result.decorators
    deco = result.decorators[0].decorator
    assert isinstance(deco, cst.Call)
    assert isinstance(deco.func, cst.Attribute)
    assert deco.func.attr.value == "parametrize"


def test_convert_non_convertible_returns_none():
    code = """
def test_example(self):
    for i in range(1000):
        with self.subTest(i=i):
            assert i >= 0
"""

    func = _parse_function(code)
    updated = func
    transformer = DummyTransformer()

    result = convert_subtest_loop_to_parametrize(func, updated, transformer)
    assert result is None
