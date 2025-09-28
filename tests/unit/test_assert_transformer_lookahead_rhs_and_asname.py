import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import wrap_assert_logs_in_block


def _with_assertlogs_as_log(inner_stmts):
    # build a With with self.assertLogs(... ) as log
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertLogs")),
            args=[cst.Arg(value=cst.SimpleString(value='"root"')), cst.Arg(value=cst.SimpleString(value='"INFO"'))],
        ),
        asname=cst.AsName(name=cst.Name(value="log")),
    )
    return cst.With(body=cst.IndentedBlock(body=inner_stmts), items=[with_item])


def test_with_assertRaises_preserves_asname():
    # Create With with assertRaises and an asname
    item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertRaises")),
            args=[cst.Arg(value=cst.Name(value="ValueError"))],
        ),
        asname=cst.AsName(name=cst.Name(value="e")),
    )
    w = cst.With(body=cst.IndentedBlock(body=[cst.Pass()]), items=[item])
    out = wrap_assert_logs_in_block([w])
    assert len(out) == 1
    new_w = out[0]
    assert isinstance(new_w, cst.With)
    # the converted item should have the asname preserved
    assert new_w.items and new_w.items[0].asname is not None
    assert isinstance(new_w.items[0].asname, cst.AsName)
    assert new_w.items[0].asname.name.value == "e"


def test_attribute_equality_rewritten_to_caplog_records_inside_with():
    # Place the assert after the With so the lookahead rewrite path is used
    with_stmt = _with_assertlogs_as_log([cst.Pass()])
    following_assert = cst.SimpleStatementLine(
        body=[
            cst.Assert(
                test=cst.Comparison(
                    left=cst.Attribute(value=cst.Name(value="log"), attr=cst.Name(value="output")),
                    comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.SimpleString(value="'x'"))],
                )
            )
        ]
    )

    out = wrap_assert_logs_in_block([with_stmt, following_assert])
    code = cst.Module(body=out).code
    assert "caplog.records" in code


def test_rhs_attribute_lookahead_rewrite_changes_rhs_to_caplog_records():
    # with ... as log
    with_stmt = _with_assertlogs_as_log([cst.Pass()])
    # following assert: foo == log.output
    s = cst.SimpleStatementLine(
        body=[
            cst.Assert(
                test=cst.Comparison(
                    left=cst.Name(value="foo"),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.Equal(),
                            comparator=cst.Attribute(value=cst.Name(value="log"), attr=cst.Name(value="output")),
                        )
                    ],
                )
            )
        ]
    )
    out = wrap_assert_logs_in_block([with_stmt, s])
    code = cst.Module(body=out).code
    assert "caplog.records" in code


def test_rhs_subscript_getmessage_transformed_by_lookahead():
    with_stmt = _with_assertlogs_as_log([cst.Pass()])
    # following assert: foo == log.output[0]
    s = cst.SimpleStatementLine(
        body=[
            cst.Assert(
                test=cst.Comparison(
                    left=cst.Name(value="foo"),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.Equal(),
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
    out = wrap_assert_logs_in_block([with_stmt, s])
    code = cst.Module(body=out).code
    # expecting .getMessage() inserted
    assert ".getMessage(" in code or "caplog.records" in code
