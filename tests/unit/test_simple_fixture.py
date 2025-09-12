import libcst as cst
from typing import cast

from splurge_unittest_to_pytest.converter.simple_fixture import (
    create_simple_fixture,
)


def code_for(node: cst.CSTNode) -> str:
    if isinstance(node, cst.FunctionDef):
        return cst.Module(body=[node]).code.strip()
    return cst.Module(body=[cst.SimpleStatementLine([cst.Expr(cast(cst.BaseExpression, node))])]).code.strip()


def test_create_simple_fixture_function_and_decorator():
    func = create_simple_fixture("val", cst.Integer("1"))
    code = code_for(func)
    assert "def val(" in code
    # The helper deliberately does not add the decorator; caller must add it
    assert "@pytest.fixture" not in code
    assert "return 1" in code


def test_create_simple_fixture_returns_value():
    node = create_simple_fixture("x", cst.Integer("5"))
    # create_simple_fixture returns a FunctionDef; place it directly in a Module
    code = cst.Module(body=[node]).code
    assert "return 5" in code
