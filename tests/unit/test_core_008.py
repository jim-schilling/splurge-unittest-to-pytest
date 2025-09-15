import libcst as cst

from splurge_unittest_to_pytest.converter import assertions

DOMAINS = ["core"]


def _wrap_assert(node: cst.Assert) -> str:
    stmt = cst.SimpleStatementLine(body=[node])
    return cst.Module(body=[stmt]).code


def test_comparison_assertions_greater_less():
    gt = assertions._assert_greater([cst.Arg(value=cst.Integer("2")), cst.Arg(value=cst.Integer("1"))])
    gte = assertions._assert_greater_equal([cst.Arg(value=cst.Integer("2")), cst.Arg(value=cst.Integer("2"))])
    lt = assertions._assert_less([cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.Integer("2"))])
    lte = assertions._assert_less_equal([cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.Integer("1"))])

    assert ">" in _wrap_assert(gt) or "==" in _wrap_assert(gt)
    assert ">=" in _wrap_assert(gte) or ">=" in _wrap_assert(gte)
    assert "<" in _wrap_assert(lt)
    assert "<=" in _wrap_assert(lte)


def test_assertions_map_contains_expected_keys():
    # Ensure common assert names are present in the public ASSERTIONS_MAP
    keys = assertions.ASSERTIONS_MAP.keys()
    assert "assertEqual" in keys
    assert "assertTrue" in keys
    assert "assertIsNone" in keys
