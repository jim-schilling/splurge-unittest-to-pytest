import libcst as cst
import pytest

from splurge_unittest_to_pytest.transformers import assert_transformer as at


def _call_from_code(src: str) -> cst.Call:
    module = cst.parse_module(src)
    # assume single expression like: self.assertEqual(a, b)
    expr = module.body[0]
    if isinstance(expr, cst.SimpleStatementLine) and isinstance(expr.body[0], cst.Expr):
        value = expr.body[0].value
        if isinstance(value, cst.Call):
            return value
    raise AssertionError("Unable to parse call from src")


def _code_of_call(node: cst.Call) -> str:
    # Wrap in a simple statement to generate code comparable to expected
    return cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=node)])]).code.strip()


@pytest.mark.parametrize(
    "src, expected",
    [
        ("self.assertEqual(a, b)", "assert a == b"),
        ("self.assertDictEqual(d1, d2)", "assert d1 == d2"),
    ],
)
def test_transform_assert_equal_and_dict(src: str, expected: str):
    """Test basic assertEqual and assertDictEqual transformations."""
    call = _call_from_code(src)
    out = (
        at.transform_assert_equal(call)
        if "Equal(" in src and "Dict" not in src
        else at.transform_assert_dict_equal(call)
    )
    assert _code_of_call(out) == expected


@pytest.mark.parametrize(
    "src, expected",
    [
        ("self.assertTrue(x)", "assert x"),
        ("self.assertFalse(x)", "assert not x"),
        ("self.assertIs(a, b)", "assert a is b"),
        ("self.assertIn(item, container)", "assert item in container"),
    ],
)
def test_transform_simple_asserts(src: str, expected: str):
    call = _call_from_code(src)
    # dispatch
    name = src.split(".")[1].split("(")[0]
    mapper = {
        "assertTrue": at.transform_assert_true,
        "assertFalse": at.transform_assert_false,
        "assertIs": at.transform_assert_is,
        "assertIn": at.transform_assert_in,
    }
    out = mapper[name](call)
    assert _code_of_call(out) == expected


@pytest.mark.parametrize(
    "src, contains",
    [
        ("self.assertRaises(ValueError, func)", "pytest.raises"),
        ("self.assertRaisesRegex(ValueError, 'pat', func)", "pytest.raises"),
    ],
)
def test_transform_raises_variants(src: str, contains: str):
    call = _call_from_code(src)
    fn = at.transform_assert_raises if "Raises(" in src and "Regex" not in src else at.transform_assert_raises_regex
    out = fn(call)
    assert contains in _code_of_call(out)


@pytest.mark.parametrize(
    "src, expected",
    [
        ("self.assertIsInstance(obj, MyClass)", "assert isinstance(obj, MyClass)"),
        ("self.assertNotIsInstance(obj, MyClass)", "assert not isinstance(obj, MyClass)"),
        ("self.assertSetEqual(s1, s2)", "assert s1 == s2"),
        ("self.assertTupleEqual(t1, t2)", "assert t1 == t2"),
    ],
)
def test_transform_instance_and_collections(src: str, expected: str):
    call = _call_from_code(src)
    # dispatch mapping for these tests
    mapper = {
        "assertIsInstance": at.transform_assert_isinstance,
        "assertNotIsInstance": at.transform_assert_not_isinstance,
        "assertSetEqual": at.transform_assert_set_equal,
        "assertTupleEqual": at.transform_assert_tuple_equal,
    }
    name = src.split(".")[1].split("(")[0]
    out = mapper[name](call)
    assert _code_of_call(out) == expected


def test_malformed_and_negative_inputs():
    # Calls with too few args should be returned unchanged
    call_short = _call_from_code("self.assertEqual(a)")
    out_short = at.transform_assert_equal(call_short)
    assert _code_of_call(out_short) == _code_of_call(call_short)

    # Completely different call should be unchanged
    call_other = _call_from_code("self.someOtherCall(a)")
    # use a transformer that requires 2 args -> should be unchanged
    out_other = at.transform_assert_list_equal(call_other)
    assert _code_of_call(out_other) == _code_of_call(call_other)


@pytest.mark.parametrize(
    "transform_fn, call_src",
    [
        (at.transform_assert_equal, "self.assertEqual(a)"),
        (at.transform_assert_dict_equal, "self.assertDictEqual(d1)"),
        (at.transform_assert_list_equal, "self.assertListEqual(l1)"),
        (at.transform_assert_set_equal, "self.assertSetEqual(s1)"),
        (at.transform_assert_tuple_equal, "self.assertTupleEqual(t1)"),
        (at.transform_assert_is, "self.assertIs(a)"),
        (at.transform_assert_in, "self.assertIn(x)"),
        (at.transform_assert_raises, "self.assertRaises(ValueError)"),
        (at.transform_assert_raises_regex, "self.assertRaisesRegex(ValueError, 'p')"),
        (at.transform_assert_isinstance, "self.assertIsInstance(o)"),
        (at.transform_assert_not_isinstance, "self.assertNotIsInstance(o)"),
        (at.transform_assert_true, "self.assertTrue()"),
        (at.transform_assert_false, "self.assertFalse()"),
    ],
)
def test_negative_insufficient_args(transform_fn, call_src):
    """Each transform should leave calls with insufficient args unchanged."""
    call = _call_from_code(call_src)
    out = transform_fn(call)
    assert _code_of_call(out) == _code_of_call(call)


def test_transform_list_equal_specific():
    call = _call_from_code("self.assertListEqual(list_a, list_b)")
    out = at.transform_assert_list_equal(call)
    assert _code_of_call(out) == "assert list_a == list_b"


# Edge case tests for transformation robustness
@pytest.mark.parametrize(
    "src, expected",
    [
        # Complex expressions
        ("self.assertEqual(a + b, c * d)", "assert a + b == c * d"),
        ("self.assertEqual(func(x, y), obj.method(z))", "assert func(x, y) == obj.method(z)"),
        ("self.assertTrue(a and b or c)", "assert a and b or c"),
        ("self.assertFalse(not x)", "assert not not x"),
        # Nested calls
        ("self.assertEqual(len(items), count)", "assert len(items) == count"),
        ("self.assertEqual(sum(values), total)", "assert sum(values) == total"),
        # String and numeric literals
        ("self.assertEqual(x, 42)", "assert x == 42"),
        ("self.assertEqual(name, 'test')", "assert name == 'test'"),
        ("self.assertEqual(flag, True)", "assert flag == True"),
        ("self.assertEqual(value, None)", "assert value == None"),
    ],
)
def test_transform_assert_edge_cases_complex_expressions(src: str, expected: str):
    """Test assert transformations with complex expressions."""
    call = _call_from_code(src)

    # Determine which transformer to use based on the assertion type
    if "assertEqual" in src:
        out = at.transform_assert_equal(call)
    elif "assertTrue" in src:
        out = at.transform_assert_true(call)
    elif "assertFalse" in src:
        out = at.transform_assert_false(call)
    else:
        pytest.fail(f"No transformer found for {src}")

    assert _code_of_call(out) == expected


@pytest.mark.parametrize(
    "src",
    [
        # Missing arguments
        "self.assertEqual(x)",
        "self.assertEqual()",
        "self.assertTrue()",
        "self.assertFalse(y, z)",  # Too many args
        # Wrong argument types (should not crash)
        "self.assertEqual(123, 'string')",  # Valid but unusual
        "self.assertTrue(None)",
        "self.assertFalse(0)",
    ],
)
def test_transform_assert_edge_cases_argument_variations(src: str):
    """Test assert transformations handle unusual argument patterns gracefully."""
    try:
        call = _call_from_code(src)

        # Try to transform - should not crash even with unusual arguments
        if "assertEqual" in src:
            result = at.transform_assert_equal(call)
        elif "assertTrue" in src:
            result = at.transform_assert_true(call)
        elif "assertFalse" in src:
            result = at.transform_assert_false(call)
        else:
            pytest.fail(f"No transformer found for {src}")

        # Result should be a valid CST node (either transformed Assert or original Call)
        assert isinstance(result, cst.Assert | cst.Call)

    except Exception as e:
        # If parsing fails, that's acceptable for malformed input
        if "Unable to parse call from src" in str(e):
            pytest.skip(f"Cannot parse malformed input: {src}")
        else:
            # Unexpected error - re-raise
            raise


def test_transform_assert_boundary_conditions():
    """Test assert transformations at boundary conditions."""

    # Empty strings and zero values
    test_cases = [
        ("self.assertEqual('', '')", "assert '' == ''"),
        ("self.assertEqual(0, 0)", "assert 0 == 0"),
        ("self.assertEqual([], [])", "assert [] == []"),
        ("self.assertEqual({}, {})", "assert {} == {}"),
        ("self.assertTrue(True)", "assert True"),
        ("self.assertFalse(False)", "assert not False"),
    ]

    for src, expected in test_cases:
        call = _call_from_code(src)

        if "assertEqual" in src:
            out = at.transform_assert_equal(call)
        elif "assertTrue" in src:
            out = at.transform_assert_true(call)
        elif "assertFalse" in src:
            out = at.transform_assert_false(call)
        else:
            continue

        assert _code_of_call(out) == expected


def test_transform_assert_malformed_input_handling():
    """Test that transformers handle malformed CST input gracefully."""

    # Create a malformed CST node (missing required attributes)
    malformed_call = cst.Call(
        func=cst.Name("assertEqual"),
        args=[],  # Missing required arguments
    )

    # Should not crash, should return the original call
    result = at.transform_assert_equal(malformed_call)
    assert result == malformed_call  # Should return unchanged


def test_transform_assert_none_values():
    """Test assert transformations with None values."""

    test_cases = [
        ("self.assertIsNone(x)", "assert x is None"),
        ("self.assertIsNotNone(y)", "assert y is not None"),
        ("self.assertEqual(a, None)", "assert a == None"),
        ("self.assertTrue(x is None)", "assert x is None"),
    ]

    for src, expected in test_cases:
        call = _call_from_code(src)

        if "assertIsNone" in src:
            out = at.transform_assert_is_none(call)
        elif "assertIsNotNone" in src:
            out = at.transform_assert_is_not_none(call)
        elif "assertEqual" in src:
            out = at.transform_assert_equal(call)
        elif "assertTrue" in src:
            out = at.transform_assert_true(call)
        else:
            continue

        assert _code_of_call(out) == expected
