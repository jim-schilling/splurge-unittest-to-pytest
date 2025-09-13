import libcst as cst
from typing import cast

from splurge_unittest_to_pytest.converter.decorators import (
    build_pytest_fixture_decorator,
)


def render(node: cst.CSTNode) -> str:
    return cst.Module(body=[cst.SimpleStatementLine([cst.Expr(cast(cst.BaseExpression, node))])]).code.strip()


def test_build_basic_fixture_decorator():
    dec = build_pytest_fixture_decorator()
    code = render(dec)
    assert "@pytest.fixture" in code


def test_build_fixture_decorator_rejects_kwargs():
    try:
        _ = build_pytest_fixture_decorator(scope="module", autouse=True)  # type: ignore[arg-type]
        raised = False
    except TypeError:
        raised = True

    assert raised, "build_pytest_fixture_decorator should not accept kwargs"


def test_build_pytest_fixture_decorator_renders_pytest_fixture():
    dec = build_pytest_fixture_decorator()
    # Render decorator to code via a Module so we get a string representation
    code = cst.Module(
        body=[cst.SimpleStatementLine(body=[cst.Expr(value=cast(cst.BaseExpression, dec.decorator))])]
    ).code
    assert "pytest.fixture" in code
