import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import wrap_assert_logs_in_block


def _make_assert_len_on_log_output(equal_to: int, use_subscript: bool = False) -> cst.Assert:
    # build len(log.output) or len(log.output[0]) == N
    attr = cst.Attribute(value=cst.Name(value="log"), attr=cst.Name(value="output"))
    if use_subscript:
        sub = cst.Subscript(value=attr, slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Integer(value="0")))])
        call_arg = sub
    else:
        call_arg = attr

    len_call = cst.Call(func=cst.Name(value="len"), args=[cst.Arg(value=call_arg)])
    comp = cst.Comparison(
        left=len_call,
        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer(value=str(equal_to)))],
    )
    return cst.Assert(test=comp)


def test_with_inner_assert_node_rewrites_attribute_and_subscript():
    # With having asname alias 'log' and inner Assert node
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertLogs")),
            args=[
                cst.Arg(value=cst.SimpleString(value="'my.logger'")),
                cst.Arg(keyword=cst.Name(value="level"), value=cst.SimpleString(value='"INFO"')),
            ],
        ),
        asname=cst.AsName(name=cst.Name(value="log")),
    )

    # Inner assert as Assert node
    inner_assert = _make_assert_len_on_log_output(2, use_subscript=False)
    with_node = cst.With(body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[inner_assert])]), items=[with_item])

    out = wrap_assert_logs_in_block([with_node])
    code = cst.Module(body=out).code
    assert "caplog.records" in code
    assert "len(caplog.records)" in code
    assert "log.output" not in code


def test_lookahead_rewrites_following_asserts_after_with():
    # With with alias, followed by separate assert statements that reference alias
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertLogs")),
            args=[cst.Arg(value=cst.SimpleString(value="'my.logger'"))],
        ),
        asname=cst.AsName(name=cst.Name(value="log")),
    )

    with_node = cst.With(
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))])]),
        items=[with_item],
    )

    # Following assertions outside the with
    assert1 = cst.SimpleStatementLine(
        body=[
            cst.Assert(
                test=cst.Comparison(
                    left=cst.Call(
                        func=cst.Name(value="len"),
                        args=[cst.Arg(value=cst.Attribute(value=cst.Name(value="log"), attr=cst.Name(value="output")))],
                    ),
                    comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer(value="1"))],
                )
            )
        ]
    )

    # membership with subscript
    membership = cst.SimpleStatementLine(
        body=[
            cst.Assert(
                test=cst.Comparison(
                    left=cst.SimpleString(value='"oops"'),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.In(),
                            comparator=cst.Subscript(
                                value=cst.Attribute(value=cst.Name(value="log"), attr=cst.Name(value="output")),
                                slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Integer(value="0")))],
                            ),
                        )
                    ],
                )
            )
        ]
    )

    stmts = [with_node, assert1, membership]
    out = wrap_assert_logs_in_block(stmts)
    code = cst.Module(body=out).code
    assert "caplog.records" in code
    assert ".getMessage()" in code
