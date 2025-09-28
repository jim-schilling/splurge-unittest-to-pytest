import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    transform_caplog_alias_string_fallback,
    wrap_assert_logs_in_block,
)


def _stmt(code: str) -> cst.SimpleStatementLine:
    m = cst.parse_module(code)
    for s in m.body:
        if isinstance(s, cst.SimpleStatementLine):
            return s
    raise AssertionError("no simple stmt")


def test_assert_nologs_bare_call_uses_caplog_at_level_and_pass():
    stmt = _stmt("self.assertNoLogs('root', level='DEBUG')")
    out = wrap_assert_logs_in_block([stmt])
    assert len(out) == 1
    w = out[0]
    assert isinstance(w, cst.With)
    # should have caplog.at_level as the with item
    assert w.items and isinstance(w.items[0].item, cst.Call)
    assert w.items[0].item.func.attr.value == "at_level" or w.items[0].item.func.attr.value == "at_level"


def test_assert_warnsregex_with_match_kw_converted_to_pytest_warns():
    stmt = _stmt("self.assertWarnsRegex(ValueError, 'msg')")
    out = wrap_assert_logs_in_block([stmt, _stmt("pass")])
    assert isinstance(out[0], cst.With)
    w = out[0]
    # check pytest.warns and match kw present
    assert w.items and isinstance(w.items[0].item, cst.Call)
    call = w.items[0].item
    assert call.func.attr.value == "warns"
    # match should be present in args (keyword)
    found = any(a.keyword and getattr(a.keyword, "value", None) == "match" for a in call.args)
    assert found


def test_lookahead_rewrite_rewrites_following_asserts_using_alias():
    # Create an initial With that has asname 'log' and then several following statements referencing it
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertLogs")),
            args=[cst.Arg(value=cst.SimpleString(value='"root"'))],
        ),
        asname=cst.AsName(name=cst.Name(value="log")),
    )
    with_stmt = cst.With(body=cst.IndentedBlock(body=[cst.Pass()]), items=[with_item])

    # Following statements to be lookahead-rewritten
    s1 = cst.SimpleStatementLine(
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
    s2 = cst.SimpleStatementLine(
        body=[
            cst.Assert(
                test=cst.Comparison(
                    left=cst.SimpleString(value="'x'"),
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

    stmts = [with_stmt, s1, s2]
    out = wrap_assert_logs_in_block(stmts)
    # After wrapping we should have a With and the lookahead loop should have rewritten s1/s2 in-place
    assert any("caplog.records" in cst.Module(body=out).code for _ in (0,))


def test_string_fallback_handles_log_output_and_membership():
    code = "if 'x' in log.output[0]: pass\nlen(log.output) == 1\n"
    out = transform_caplog_alias_string_fallback(code)
    assert "caplog.records" in out
    assert ".getMessage()" in out
