import libcst as cst

from splurge_unittest_to_pytest.transformers.subtest_transformer import (
    convert_simple_subtests_to_parametrize,
)


class DummyTransformer:
    def __init__(self):
        self.needs_pytest_import = False


def _get_function(code: str) -> cst.FunctionDef:
    module = cst.parse_module(code)
    for node in module.body:
        if isinstance(node, cst.FunctionDef):
            return node
    raise AssertionError("No function found in code")


def _code_has_values(func_node: cst.FunctionDef, values: list[str]) -> bool:
    s = cst.Module([func_node]).code
    for v in values:
        if str(v) not in s:
            return False
    return True


def test_list_extraction():
    code = """
def test_examples():
    for v in [1, 2, 3]:
        with self.subTest(v):
            assert True
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is not None
    assert "parametrize" in cst.Module([res]).code
    assert transformer.needs_pytest_import is True
    assert _code_has_values(res, ["1", "2", "3"])


def test_tuple_extraction():
    code = """
def test_examples():
    for v in (10, 20):
        with self.subTest(v):
            assert True
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is not None
    assert "parametrize" in cst.Module([res]).code
    assert _code_has_values(res, ["10", "20"])


def test_range_one_arg():
    code = """
def test_examples():
    for i in range(3):
        with self.subTest(i):
            assert True
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is not None
    assert _code_has_values(res, ["0", "1", "2"])


def test_range_two_args():
    code = """
def test_examples():
    for i in range(1, 4):
        with self.subTest(i):
            assert True
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is not None
    assert _code_has_values(res, ["1", "2", "3"])


def test_range_three_args():
    code = """
def test_examples():
    for i in range(0, 6, 2):
        with self.subTest(i):
            assert True
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is not None
    assert _code_has_values(res, ["0", "2", "4"])


def test_range_too_large():
    code = """
def test_examples():
    for i in range(0, 50):
        with self.subTest(i):
            assert True
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is None


def test_range_non_literal_arg():
    code = """
def test_examples():
    n = 3
    for i in range(n):
        with self.subTest(i):
            assert True
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    # Because range arg is a Name in the call, conversion should not happen
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is None


def test_inner_body_disallowed_stmt():
    # inner body contains a Return which is not one of allowed simple types
    code = """
def test_examples():
    for v in [1]:
        with self.subTest(v):
            return
"""
    func = _get_function(code)
    transformer = DummyTransformer()
    res = convert_simple_subtests_to_parametrize(func, func, transformer)
    assert res is None
