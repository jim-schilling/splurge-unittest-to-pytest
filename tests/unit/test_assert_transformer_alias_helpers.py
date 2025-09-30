import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    AliasOutputAccess,
    _build_caplog_records_expr,
    _build_get_message_call,
    _extract_alias_output_slices,
)


def _expr(code: str) -> cst.BaseExpression:
    return cst.parse_expression(code)


def _render(expr: cst.BaseExpression) -> str:
    module = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=expr)])])
    return module.code.strip()


def test_extract_alias_output_slices_returns_alias_and_slices():
    expr = _expr("log.output[1]['msg']")
    access = _extract_alias_output_slices(expr)

    assert access is not None
    assert isinstance(access, AliasOutputAccess)
    assert access.alias_name == "log"
    assert len(access.slices) == 2

    rebuilt = _build_caplog_records_expr(access)
    assert _render(rebuilt) == "caplog.records[1]['msg']"


def test_extract_alias_output_slices_returns_none_for_non_output():
    expr = _expr("log.data[0]")
    assert _extract_alias_output_slices(expr) is None


def test_build_caplog_records_expr_without_slices():
    expr = _expr("log.output")
    access = _extract_alias_output_slices(expr)
    assert access is not None
    assert access.slices == ()

    rebuilt = _build_caplog_records_expr(access)
    assert _render(rebuilt) == "caplog.records"


def test_build_get_message_call_preserves_slice_chain():
    expr = _expr("log.output[2]['debug']")
    access = _extract_alias_output_slices(expr)
    assert access is not None

    call = _build_get_message_call(access)
    module = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=call)])])
    assert module.code.strip() == "caplog.records[2]['debug'].getMessage()"
