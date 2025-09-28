import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_transformer as at


def _call_from_code(src: str) -> cst.Call:
    mod = cst.parse_module(src)
    # assume a single Expr wrapping a Call
    node = mod.body[0]
    if isinstance(node, cst.SimpleStatementLine):
        expr = node.body[0]
        if isinstance(expr, cst.Expr) and isinstance(expr.value, cst.Call):
            return expr.value
    raise AssertionError("Couldn't parse call from src")


def test_transform_assert_almost_equal_to_approx():
    call = _call_from_code("assertAlmostEqual(a, b)")
    out = at.transform_assert_almost_equal(call)
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=out)])]).code
    assert "pytest.approx" in code or "approx(" in code


def test_transform_assert_raises_regex_needs_three_args():
    # ensure conservative behavior: only transform when exc, callable, regex provided
    call2 = _call_from_code("assertRaisesRegex(ValueError, func)")
    out2 = at.transform_assert_raises_regex(call2)
    # should return original-like node when not enough args
    assert isinstance(out2, cst.Call)

    call3 = _call_from_code("assertRaisesRegex(ValueError, func, 'msg')")
    out3 = at.transform_assert_raises_regex(call3)
    code3 = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=out3)])]).code
    assert "pytest.raises" in code3
