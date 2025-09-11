"""Small helper to build a simple fixture that returns a value."""

from __future__ import annotations

import libcst as cst


def create_simple_fixture(attr_name: str, value_expr: cst.BaseExpression) -> cst.FunctionDef:
    """Return a fixture FunctionDef that simply returns value_expr.

    Adds no decorators; caller should add @pytest.fixture as needed.
    """
    # Create a simple return statement
    ret = cst.SimpleStatementLine(body=[cst.Return(value=value_expr)])
    body = cst.IndentedBlock(body=[ret])

    func = cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(),
        body=body,
        decorators=[],
        returns=None,
        asynchronous=None,
    )
    return func
