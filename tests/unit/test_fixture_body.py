import libcst as cst

from splurge_unittest_to_pytest.converter.fixture_body import build_fixture_body


def test_build_fixture_body_with_literal():
    body = build_fixture_body("foo", cst.Integer("1"), [])
    # Should yield the literal directly
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=body)])]).code
    assert "yield 1" in code


def test_build_fixture_body_with_bound_value_and_cleanup():
    cleanup_src = "self.foo.close()"
    cleanup_stmt = cst.parse_statement(cleanup_src)
    body = build_fixture_body("foo", cst.Call(func=cst.Name("make"), args=[]), [cleanup_stmt])
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=body)])]).code
    # Should have assignment and yield and cleanup referencing the local value name
    assert "_=foo_value" not in code  # ensure we use the exact name pattern below
    assert "_foo_value =" in code
    assert "yield _foo_value" in code
    assert "_foo_value.close()" in code
