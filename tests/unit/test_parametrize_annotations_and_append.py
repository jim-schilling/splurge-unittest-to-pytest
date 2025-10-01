import libcst as cst

from splurge_unittest_to_pytest.transformers.parametrize_helper import convert_subtest_loop_to_parametrize


class TransformerWithOptions:
    def __init__(self) -> None:
        self.needs_pytest_import = False
        self.parametrize_include_ids = True
        self.parametrize_add_annotations = True


def _parse_function(code: str) -> cst.FunctionDef:
    module = cst.parse_module(code)
    for stmt in module.body:
        if isinstance(stmt, cst.FunctionDef):
            return stmt
    raise AssertionError("no function found in code")


def test_annotations_added_when_requested():
    code = """
def test_ann(self):
    for x in [1, 2]:
        with self.subTest(x=x):
            assert x
"""
    func = _parse_function(code)
    transformer = TransformerWithOptions()
    result = convert_subtest_loop_to_parametrize(func, func, transformer)
    assert result is not None
    # Ensure parameter annotation was added (int inferred)
    params = result.params
    # The last param should be named 'x' and have an annotation
    assert params.params
    last = params.params[-1]
    assert last.name.value == "x"
    assert last.annotation is not None


def test_append_rows_to_existing_parametrize():
    # Build a function that already has a parametrize decorator for 'a'
    module = cst.parse_module(
        """
@pytest.mark.parametrize('a', [1])
def test_append(self):
    b_vals = [2]
    for b in b_vals:
        with self.subTest(b=b):
            assert b
"""
    )
    # Extract function def
    func = None
    for stmt in module.body:
        if isinstance(stmt, cst.FunctionDef):
            func = stmt
            break
    assert func is not None

    # Call conversion; it should append rows to existing decorator only if param names differ
    transformer = TransformerWithOptions()
    transformer.parametrize_add_annotations = False
    result = convert_subtest_loop_to_parametrize(func, func, transformer)
    # Conversion should be refused when a different parametrize decorator
    # already exists on the function (module behavior)
    assert result is None
