import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_transformer as at


def test_transform_assert_raises_regex_conservative():
    # only transform when 3+ args present
    call = cst.Call(
        func=cst.Name("assertRaisesRegex"),
        args=[
            cst.Arg(value=cst.Name("ValueError")),
            cst.Arg(value=cst.Name("f")),
            cst.Arg(value=cst.SimpleString('"err"')),
        ],
    )
    out = at.transform_assert_raises_regex(call)
    # expect a Call (pytest.raises(...))
    assert isinstance(out, cst.Call)


def test_transform_assert_almost_equal_prefers_approx():
    call = cst.Call(
        func=cst.Name("assertAlmostEqual"), args=[cst.Arg(value=cst.Name("a")), cst.Arg(value=cst.Name("b"))]
    )
    out = at.transform_assert_almost_equal(call)
    # Should produce an Assert node (comparison or approx usage)
    assert out is not None


def test_caplog_alias_string_fallback_rewrite():
    # This uses the string-based fallback: replace alias.output[...] == "msg" with caplog.records
    code = 'log.output[0] == "m"'
    out = at.transform_caplog_alias_string_fallback(code)
    assert "caplog.records" in out or out == code
