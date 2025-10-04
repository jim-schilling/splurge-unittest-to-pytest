import libcst as cst

from splurge_unittest_to_pytest.transformers.transformer_helper import (
    wrap_small_stmt_if_needed,
)


def test_wraps_base_small_statement_assert():
    # Use a valid identifier for Name; keep the assert test simple.
    node = cst.Assert(test=cst.Name("x"))
    wrapped = wrap_small_stmt_if_needed(node)
    assert isinstance(wrapped, cst.SimpleStatementLine)
    assert isinstance(wrapped.body[0], cst.BaseSmallStatement)


def test_returns_base_statement_unchanged():
    # If node is already a compound statement (If), it should be returned as-is
    node = cst.If(test=cst.Name("cond"), body=cst.IndentedBlock(body=[]))
    got = wrap_small_stmt_if_needed(node)
    assert got is node


def test_wraps_expression_into_expr_statement():
    node = cst.Call(func=cst.Name("do_side_effect"), args=[])
    wrapped = wrap_small_stmt_if_needed(node)
    assert isinstance(wrapped, cst.SimpleStatementLine)
    assert isinstance(wrapped.body[0], cst.Expr)
    assert isinstance(wrapped.body[0].value, cst.Call)


def test_fallback_returns_pass_on_unexpected_node():
    # Create a custom dummy node subclass of CSTNode that is neither
    # a BaseStatement nor a BaseExpression to trigger the fallback.
    # Use a plain object which is not a libcst node to trigger the
    # conservative fallback path. Subclassing cst.CSTNode directly is
    # abstract and cannot be instantiated.
    dummy = object()
    wrapped = wrap_small_stmt_if_needed(dummy)
    assert isinstance(wrapped, cst.SimpleStatementLine)
    assert isinstance(wrapped.body[0], cst.Pass)
