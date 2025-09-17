"""Small helper to build a simple fixture that returns a value.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

import libcst as cst

DOMAINS = ["converter", "fixtures"]

# Associated domains for this module


def create_simple_fixture(attr_name: str, value_expr: cst.BaseExpression) -> cst.FunctionDef:
    """Return a fixture FunctionDef that simply returns value_expr.

    Adds no decorators; caller should add @pytest.fixture as needed.
    """

    # Conservative local inference for simple literals/containers to avoid
    # adding a dependency on other converter modules and to keep this helper
    # self-contained.
    def _infer_simple_return_annotation(expr: cst.BaseExpression | None) -> cst.Annotation | None:
        if expr is None:
            return None
        if isinstance(expr, cst.Integer):
            return cst.Annotation(annotation=cst.Name("int"))
        if isinstance(expr, cst.Float):
            return cst.Annotation(annotation=cst.Name("float"))
        if isinstance(expr, cst.SimpleString):
            return cst.Annotation(annotation=cst.Name("str"))
        if isinstance(expr, cst.List):
            return cst.Annotation(annotation=cst.Name("List"))
        if isinstance(expr, cst.Tuple):
            return cst.Annotation(annotation=cst.Name("Tuple"))
        if isinstance(expr, cst.Set):
            return cst.Annotation(annotation=cst.Name("Set"))
        if isinstance(expr, cst.Dict):
            return cst.Annotation(annotation=cst.Name("Dict"))
        return None

    # Create a simple return statement
    ret = cst.SimpleStatementLine(body=[cst.Return(value=value_expr)])
    body = cst.IndentedBlock(body=[ret])

    func = cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(),
        body=body,
        decorators=[],
        returns=_infer_simple_return_annotation(value_expr),
        asynchronous=None,
    )
    return func
