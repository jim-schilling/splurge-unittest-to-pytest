import libcst as cst

from splurge_unittest_to_pytest.converter.fixture_function import create_fixture_function

DOMAINS = ["converter", "fixtures"]


def test_create_fixture_function_builds_function():
    # Build a minimal body
    body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(value=cst.Integer("1"))])])
    dec = cst.Decorator(decorator=cst.Name("fixture"))
    func = create_fixture_function("foo", body, dec)
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=func)])]).code
    assert "def foo" in code
    assert "fixture" in code
