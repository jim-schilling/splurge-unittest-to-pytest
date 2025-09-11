import libcst as cst

from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator


def test_build_pytest_fixture_decorator_renders_pytest_fixture():
    dec = build_pytest_fixture_decorator()
    # Render decorator to code via a Module so we get a string representation
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=dec.decorator)])]).code
    assert "pytest.fixture" in code
