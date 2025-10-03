import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as aw


def test_rewrite_equality_subscript_to_getmessage():
    # left side is my_alias.output[0] == something
    left = cst.Subscript(
        value=cst.Attribute(value=cst.Name(value="my_alias"), attr=cst.Name(value="output")),
        slice=(
            cst.SubscriptElement(
                cst.Index(value=cst.Integer(value="0")),
            ),
        ),
    )
    comp = cst.Comparison(
        left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer(value="1"))]
    )

    out = aw._rewrite_equality_comparison(comp, alias_name="my_alias")
    assert out is not None
    assert isinstance(out.left, cst.Call)
    assert isinstance(out.left.func, cst.Attribute)
    assert out.left.func.attr.value == "getMessage"


def test_rewrite_equality_attribute_to_caplog_records():
    # left side is my_alias.output == something
    left = cst.Attribute(value=cst.Name(value="my_alias"), attr=cst.Name(value="output"))
    comp = cst.Comparison(
        left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer(value="1"))]
    )

    out = aw._rewrite_equality_comparison(comp, alias_name="my_alias")
    assert out is not None
    assert isinstance(out.left, cst.Subscript) or isinstance(out.left, cst.Attribute)

    # caplog.records should be present somewhere in the left expression
    # Walk down to find 'caplog' name
    def has_caplog(node):
        if isinstance(node, cst.Attribute) and isinstance(node.value, cst.Name) and node.value.value == "caplog":
            return True
        for field in getattr(node, "__dict__", {}).values():
            if isinstance(field, cst.CSTNode):
                if has_caplog(field):
                    return True
        return False

    assert has_caplog(out.left)
