import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import AssertionRewriter


def _render_assert(node: cst.BaseSmallStatement) -> str:
    # wrap in module to render consistently
    mod = cst.Module(body=[cst.SimpleStatementLine(body=[node])])
    return mod.code.strip()


def test_assert_equal_and_is_none_render():
    ar = AssertionRewriter()
    # Equal
    a = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertEqual")),
        args=[cst.Arg(cst.Name("a")), cst.Arg(cst.Name("b"))],
    )
    conv = ar._convert_self_assertion_to_pytest(a)
    assert conv is not None
    assert _render_assert(conv) == "assert a == b"

    # IsNone
    a2 = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertIsNone")), args=[cst.Arg(cst.Name("x"))]
    )
    conv2 = ar._convert_self_assertion_to_pytest(a2)
    assert conv2 is not None
    assert _render_assert(conv2) == "assert x is None"
