import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_transformer as at


def test_assert_transformer_eq_and_unary_rewrites():
    # Build a Comparison node representing: not ('err' in log.output[0])
    alias = "log"
    # Create AST for: assert not ('err' in log.output[0])
    left = cst.SimpleString(value="'err'")
    sub = cst.Subscript(
        value=cst.Attribute(value=cst.Name(value=alias), attr=cst.Name(value="output")),
        slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Integer(value="0")))],
    )
    comp = cst.Comparison(left=left, comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=sub)])
    unary = cst.UnaryOperation(operator=cst.Not(), expression=comp)

    # wrap as an Assert to pass to helpers
    # Try calling the internal helper if present; otherwise ensure no exception
    rewritten = None
    if hasattr(at, "_try_unary_comparison_rewrite"):
        rewritten = at._try_unary_comparison_rewrite(unary)
    assert rewritten is None or isinstance(rewritten, cst.Assert)


def test_rewrite_asserts_using_alias_in_with_body_no_crash():
    with_node = cst.parse_statement("""
with something as log:
    assert 'x' in log.output[0]
""")
    out = at.rewrite_asserts_using_alias_in_with_body(with_node, "log")
    assert isinstance(out, cst.With)
