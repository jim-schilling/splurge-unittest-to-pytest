import libcst as cst

from splurge_unittest_to_pytest.transformers.parametrize_helper import convert_subtest_loop_to_parametrize


class DummyTransformer:
    def __init__(self) -> None:
        self.needs_pytest_import = False
        self.parametrize_include_ids = True
        self.parametrize_add_annotations = False


def _parse_function(code: str) -> cst.FunctionDef:
    module = cst.parse_module(code)
    for stmt in module.body:
        if isinstance(stmt, cst.FunctionDef):
            return stmt
    raise AssertionError("no function found in code")


def _decorate_and_result(func: cst.FunctionDef) -> cst.FunctionDef | None:
    transformer = DummyTransformer()
    return convert_subtest_loop_to_parametrize(func, func, transformer)


def test_range_conversion_small():
    code = """
def test_r(self):
    for i in range(3):
        with self.subTest(i=i):
            assert i >= 0
"""
    func = _parse_function(code)
    result = _decorate_and_result(func)
    assert result is not None


def test_enumerate_conversion_with_start():
    code = """
def test_enum(self):
    names = ['a', 'b']
    for idx, name in enumerate(names, 10):
        with self.subTest(idx=idx, name=name):
            assert name
"""
    func = _parse_function(code)
    result = _decorate_and_result(func)
    assert result is not None


def test_mapping_items_conversion():
    code = """
def test_map(self):
    data = {'x': 1, 'y': 2}
    for k, v in data.items():
        with self.subTest(k=k, v=v):
            assert k in ('x', 'y')
"""
    func = _parse_function(code)
    result = _decorate_and_result(func)
    assert result is not None


def test_name_reference_assignment_removed_when_safe():
    code = """
def test_ref(self):
    items = [(1, 2), (3, 4)]
    for a, b in items:
        with self.subTest(a=a, b=b):
            assert a < b
"""
    func = _parse_function(code)
    result = _decorate_and_result(func)
    assert result is not None
    # Ensure the original assignment was removed from the emitted body
    module = cst.Module(body=[result])
    emitted = module.code
    assert "items =" not in emitted


def test_constant_inlining_substitutes_literal():
    code = """
def test_inline(self):
    size = 5
    sizes = [size]
    for s in sizes:
        with self.subTest(s=s):
            assert s == 5
"""
    func = _parse_function(code)
    result = _decorate_and_result(func)
    assert result is not None
    # The decorator should contain the literal '5' rather than the name 'size'
    deco = result.decorators[0].decorator
    assert "5" in cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=deco)])]).code


def test_reject_non_constant_name_reference():
    code = """
def test_reject(self):
    def make_list():
        return [1,2]

    items = make_list()
    for i in items:
        with self.subTest(i=i):
            assert i
"""
    func = _parse_function(code)
    result = _decorate_and_result(func)
    assert result is None
