import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as aw


def test_rewrite_membership_in_alias_output_to_getmessage():
    # Build expression: x in my_alias.output[0]
    comp = cst.Comparison(
        left=cst.Name(value="x"),
        comparisons=[
            cst.ComparisonTarget(
                operator=cst.In(),
                comparator=cst.Subscript(
                    value=cst.Attribute(value=cst.Name(value="my_alias"), attr=cst.Name(value="output")),
                    slice=(
                        cst.SubscriptElement(
                            cst.Index(value=cst.Integer(value="0")),
                        ),
                    ),
                ),
            )
        ],
    )

    out = aw._rewrite_membership_comparison(comp, alias_name="my_alias")
    assert out is not None
    # The comparator of the first comparison should now be a Call (getMessage)
    comparator = out.comparisons[0].comparator
    assert isinstance(comparator, cst.Call)
    assert isinstance(comparator.func, cst.Attribute)
    assert comparator.func.attr.value == "getMessage"
