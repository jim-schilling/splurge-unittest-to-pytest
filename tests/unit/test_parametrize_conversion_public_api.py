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


def test_convert_subtest_with_tuple_iteration():
    """Test conversion with tuple iteration (should succeed)."""
    code = """
def test_example(self):
    items = [(1, 'a'), (2, 'b')]
    for item in items:
        with self.subTest(item=item):
            assert item[0] > 0
"""

    func = _parse_function(code)
    updated = func
    transformer = DummyTransformer()

    # This should succeed because tuple iteration is supported
    result = convert_subtest_loop_to_parametrize(func, updated, transformer)
    assert result is not None
    assert transformer.needs_pytest_import is True


def test_convert_subtest_with_tuple_unpack():
    """Test conversion with tuple unpacking in loop target."""
    code = """
def test_example(self):
    items = [(1, 'a'), (2, 'b')]
    for x, y in items:
        with self.subTest(x=x, y=y):
            assert x > 0
"""

    func = _parse_function(code)
    updated = func
    transformer = DummyTransformer()

    result = convert_subtest_loop_to_parametrize(func, updated, transformer)
    assert result is not None
    assert transformer.needs_pytest_import is True


def test_convert_subtest_with_invalid_inner_body():
    """Test conversion fails with invalid inner body."""
    code = """
def test_example(self):
    for x in [1, 2]:
        if x > 0:  # Invalid: conditional in subtest body
            with self.subTest(x=x):
                assert x > 0
"""

    func = _parse_function(code)
    updated = func
    transformer = DummyTransformer()

    # This should return None due to validation failure
    result = convert_subtest_loop_to_parametrize(func, updated, transformer)
    assert result is None


def test_convert_subtest_with_range_call():
    """Test conversion with range() call in loop."""
    code = """
def test_example(self):
    for i in range(3):
        with self.subTest(i=i):
            assert i >= 0
"""

    func = _parse_function(code)
    updated = func
    transformer = DummyTransformer()

    result = convert_subtest_loop_to_parametrize(func, updated, transformer)
    assert result is not None
    assert transformer.needs_pytest_import is True


def test_convert_subtest_with_dict_items():
    """Test conversion with dict.items() iteration."""
    code = """
def test_example(self):
    data = {'a': 1, 'b': 2}
    for key, value in data.items():
        with self.subTest(key=key, value=value):
            assert value > 0
"""

    func = _parse_function(code)
    updated = func
    transformer = DummyTransformer()

    result = convert_subtest_loop_to_parametrize(func, updated, transformer)
    assert result is not None
    assert transformer.needs_pytest_import is True


class TestParametrizeHelperErrorConditions:
    """Test error condition handling in parametrize_helper public APIs."""

    def test_convert_subtest_with_malformed_subtest_call(self):
        """Test conversion fails with malformed subTest call."""
        code = """
def test_example(self):
    for x in [1, 2]:
        with self.subTest(1, 2):  # Invalid: positional args > 1
            assert x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_non_literal_iterable(self):
        """Test conversion fails with non-literal iterable."""
        code = """
def test_example(self):
    def get_data():
        return [1, 2, 3]
    for x in get_data():  # Invalid: function call iterable
        with self.subTest(x=x):
            assert x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_mixed_subtest_args(self):
        """Test conversion fails with mixed positional and keyword subTest args."""
        code = """
def test_example(self):
    for x, y in [(1, "a"), (2, "b")]:
        with self.subTest(x, y=y):  # Invalid: mixed positional and keyword
            assert x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_return_in_body(self):
        """Test conversion fails when subTest body contains return statement."""
        code = """
def test_example(self):
    for x in [1, 2]:
        with self.subTest(x=x):
            return  # Invalid: return in subTest body
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_nested_loops(self):
        """Test conversion fails with nested loop constructs."""
        code = """
def test_example(self):
    for x in [1, 2]:
        with self.subTest(x=x):
            for y in [3, 4]:  # Invalid: nested loop
                assert y > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_conditional_statements(self):
        """Test conversion allows conditional statements (current behavior)."""
        code = """
def test_example(self):
    for x in [1, 2]:
        with self.subTest(x=x):
            if x > 1:  # Allowed: conditional
                assert x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        # Current implementation allows conditionals
        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is not None
        assert transformer.needs_pytest_import is True

    def test_convert_subtest_with_try_statements(self):
        """Test conversion allows try statements (current behavior)."""
        code = """
def test_example(self):
    for x in [1, 2]:
        with self.subTest(x=x):
            try:  # Allowed: try statement
                assert x > 0
            except:
                pass
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        # Current implementation allows try statements
        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is not None
        assert transformer.needs_pytest_import is True

    def test_convert_subtest_with_with_statements(self):
        """Test conversion allows nested with statements (current behavior)."""
        code = """
def test_example(self):
    for x in [1, 2]:
        with self.subTest(x=x):
            with open("file.txt") as f:  # Allowed: nested with
                assert x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        # Current implementation allows nested with statements
        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is not None
        assert transformer.needs_pytest_import is True

    def test_convert_subtest_with_complex_target_unpacking(self):
        """Test conversion fails with complex target unpacking."""
        code = """
def test_example(self):
    data = [(1, 2, 3), (4, 5, 6)]
    for x, *rest in data:  # Invalid: star unpacking
        with self.subTest(x=x, rest=rest):
            assert x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_attribute_targets(self):
        """Test conversion fails with attribute targets."""
        code = """
def test_example(self):
    for self.x in [1, 2]:  # Invalid: attribute target
        with self.subTest(x=self.x):
            assert self.x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_subscript_targets(self):
        """Test conversion fails with subscript targets."""
        code = """
def test_example(self):
    data = [1, 2]
    for data[0] in [3, 4]:  # Invalid: subscript target
        with self.subTest(value=data[0]):
            assert data[0] > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_empty_iterable(self):
        """Test conversion fails with empty iterable."""
        code = """
def test_example(self):
    for x in []:  # Empty iterable
        with self.subTest(x=x):
            assert x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_complex_range_args(self):
        """Test conversion fails with complex range arguments."""
        code = """
def test_example(self):
    start = 1
    for x in range(start, 10, 2):  # Complex range args
        with self.subTest(x=x):
            assert x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_invalid_dict_items(self):
        """Test conversion fails with invalid dict.items() usage."""
        code = """
def test_example(self):
    for key in {}.items():  # Invalid: dict.items() as iterable
        with self.subTest(key=key):
            assert True
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_missing_subtest_args(self):
        """Test conversion fails when subTest call missing required args."""
        code = """
def test_example(self):
    for x in [1, 2]:
        with self.subTest():  # No args
            assert x > 0
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None

    def test_convert_subtest_with_invalid_statement_type(self):
        """Test conversion fails when subTest body has invalid statement types."""
        code = """
def test_example(self):
    for x in [1, 2]:
        with self.subTest(x=x):
            class InnerClass:  # Invalid: class definition in subTest body
                pass
"""

        func = _parse_function(code)
        updated = func
        transformer = DummyTransformer()

        result = convert_subtest_loop_to_parametrize(func, updated, transformer)
        assert result is None
