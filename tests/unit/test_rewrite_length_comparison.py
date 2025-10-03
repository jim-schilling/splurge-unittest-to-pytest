import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as aw


def test_rewrite_len_alias_output_to_caplog_records():
    # Build expression len(my_alias.output[0]) == 1
    call = cst.Call(
        func=cst.Name(value="len"),
        args=[
            cst.Arg(
                value=cst.Subscript(
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
    comp = cst.Comparison(
        left=call, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer(value="1"))]
    )

    out = aw._rewrite_length_comparison(comp, alias_name="my_alias")
    assert out is not None
    # Expect left call to have caplog.records as arg
    left_call = out.left
    assert isinstance(left_call, cst.Call)
    arg0 = left_call.args[0].value
    assert isinstance(arg0, cst.Subscript) or isinstance(arg0, cst.Attribute)
