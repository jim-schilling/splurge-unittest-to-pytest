import libcst as cst
import pytest

from splurge_unittest_to_pytest.transformers import assert_transformer as at


def code_of(node) -> str:
    if isinstance(node, cst.Assert):
        mod = cst.Module(body=[cst.SimpleStatementLine(body=[node])])
    else:
        mod = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=node)])])
    return mod.code


def test_transform_assert_multiline_equal_to_assert():
    # Build a Call node that matches: self.assertMultiLineEqual(a, b)
    call = cst.Call(
        func=cst.Name("assertMultiLineEqual"),
        args=[
            cst.Arg(value=cst.SimpleString("'''line1\nline2'''")),
            cst.Arg(value=cst.SimpleString("'''line1\nline2'''")),
        ],
    )

    transformed = at.transform_assert_multiline_equal(call)

    # Expect an Assert with a Compare using the original argument nodes
    assert isinstance(transformed, cst.Assert)

    # The test ensures the assert's test is a Compare with left, comparators[0], and operator ==
    test_expr = transformed.test
    assert isinstance(test_expr, cst.Comparison) or isinstance(test_expr, cst.Compare)

    # libcst has Comparison for newer versions; Compare alias may differ, normalize
    # Extract left, comparators, and operators depending on node type
    if isinstance(test_expr, cst.Comparison):
        left = test_expr.left
        comparators = test_expr.comparisons
        # comparisons is a list of ComparisonTarget
        assert len(comparators) == 1
        comparator = comparators[0].comparator
        operator = comparators[0].operator
        # operator should be an Equal (==)
        assert type(operator).__name__ in ("Equal", "Eq")
    else:
        # fallback if using a different node model
        left = test_expr.left
        comparators = test_expr.comparators
        assert len(comparators) == 1
        comparator = comparators[0]
        operator = test_expr.ops[0]
        assert type(operator).__name__ in ("Equal", "Eq")

    # Now compare structural equality of left and the first original arg
    original_left = call.args[0].value
    original_right = call.args[1].value

    assert (
        cst.Module([cst.SimpleStatementLine([cst.Expr(original_left)])]).code
        == cst.Module([cst.SimpleStatementLine([cst.Expr(left)])]).code
    )
    assert (
        cst.Module([cst.SimpleStatementLine([cst.Expr(original_right)])]).code
        == cst.Module([cst.SimpleStatementLine([cst.Expr(comparator)])]).code
    )
