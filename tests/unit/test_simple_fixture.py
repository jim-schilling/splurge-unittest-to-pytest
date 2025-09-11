import libcst as cst

from splurge_unittest_to_pytest.converter.simple_fixture import create_simple_fixture


def test_create_simple_fixture_returns_value():
    node = create_simple_fixture("x", cst.Integer("5"))
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=node)])]).code
    assert "return 5" in code
