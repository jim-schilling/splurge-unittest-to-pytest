import libcst as cst

from splurge_unittest_to_pytest.transformers import (
    assert_ast_rewrites,
    assert_fallbacks,
    assert_with_rewrites,
)


def test_smoke_parenthesized_shims():
    expr = cst.Name(value="x")
    # call through each shim to ensure imports work and they return
    # a ParenthesizedExpression-like object or equivalent.
    p1 = assert_ast_rewrites.parenthesized_expression(expr)
    p2 = assert_fallbacks.parenthesized_expression_shim(expr)

    assert hasattr(p1, "strip")
    assert hasattr(p2, "strip")


def test_caplog_alias_extraction_shim():
    # Build a simple attribute access like `alias.output[0]` and ensure the
    # shim delegating to the original helper returns an AliasOutputAccess-like
    # object with the expected alias name.
    alias_attr = cst.Subscript(value=cst.Attribute(value=cst.Name(value="alias"), attr=cst.Name(value="output")), slice=(cst.SubscriptElement(slice=cst.Index(value=cst.Integer(value="0"))),))
    access = assert_with_rewrites._extract_alias_output_slices(alias_attr)
    assert access is not None
    assert access.alias_name == "alias"
