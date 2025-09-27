"""String-based fixture transformation helpers.

This module contains the fallback regex-based transformer that converts
`setUp`/`tearDown` methods into pytest fixtures. Kept separate from the
CST-based transformers to make testing and reuse easier.
"""

from __future__ import annotations

import re

import libcst as cst


def transform_fixtures_string_based(code: str) -> str:
    """Fallback string-based fixture transformation.

    Args:
        code: Source code to transform

    Returns:
        Transformed source with setup/teardown converted to fixtures
    """

    # Transform setUp method to setup_method fixture
    setup_pattern = r"(\s+)def setUp\(self\):(.*?)(?=\n\s*def|\n\s*@|\nclass|\nif __name__|\Z)"

    def setup_replacement(match: re.Match[str]) -> str:
        indent = match.group(1)
        setup_body = match.group(2)
        if setup_body.strip():
            return f"{indent}@pytest.fixture\n{indent}def setup_method(self):\n{setup_body}{indent}    yield\n"
        else:
            return f"{indent}@pytest.fixture\n{indent}def setup_method(self):\n{indent}    pass\n{indent}    yield\n{indent}    pass\n"

    code = re.sub(setup_pattern, setup_replacement, code, flags=re.MULTILINE | re.DOTALL)

    # Remove tearDown method (we model teardown via yield in setup fixture)
    teardown_pattern = r"(\s+)def tearDown\(self\):(.*?)(?=\n\s*def|\n\s*@|\nclass|\nif __name__|\Z)"

    def teardown_replacement(match: re.Match[str]) -> str:
        return ""

    code = re.sub(teardown_pattern, teardown_replacement, code, flags=re.MULTILINE | re.DOTALL)

    return code


def create_class_fixture(setup_class_code: list[str], teardown_class_code: list[str]) -> cst.FunctionDef:
    """Create a libcst.FunctionDef for a class-level fixture.

    Returns a libcst.FunctionDef-like object (we keep typing loose to avoid
    importing libcst at top-level here). Caller is expected to insert the
    resulting node into the module AST.
    """

    decorator = cst.Decorator(
        decorator=cst.Call(
            func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture")),
            args=[
                cst.Arg(keyword=cst.Name(value="scope"), value=cst.SimpleString(value='"class"')),
                cst.Arg(keyword=cst.Name(value="autouse"), value=cst.Name(value="True")),
            ],
        )
    )

    body_statements = []

    for setup_line in setup_class_code:
        try:
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(setup_line))]))
        except Exception:
            try:
                parsed_stmt = cst.parse_module(setup_line).body[0]
                if isinstance(parsed_stmt, cst.SimpleStatementLine):
                    body_statements.append(parsed_stmt)
            except Exception:
                body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]))

    for teardown_line in teardown_class_code:
        try:
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(teardown_line))]))
        except Exception:
            try:
                parsed_stmt = cst.parse_module(teardown_line).body[0]
                if isinstance(parsed_stmt, cst.SimpleStatementLine):
                    body_statements.append(parsed_stmt)
            except Exception:
                body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

    if not body_statements:
        body_statements = [
            cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]),
            cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]),
            cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]),
        ]

    func = cst.FunctionDef(
        name=cst.Name(value="setup_class"),
        params=cst.Parameters(params=[cst.Param(name=cst.Name(value="cls"), annotation=None)]),
        body=cst.IndentedBlock(body=body_statements),
        decorators=[decorator],
        returns=None,
    )

    return func


def create_instance_fixture(setup_code: list[str], teardown_code: list[str]) -> cst.FunctionDef:
    decorator = cst.Decorator(
        decorator=cst.Call(
            func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture")),
            args=[cst.Arg(keyword=cst.Name(value="autouse"), value=cst.Name(value="True"))],
        )
    )

    body_statements = []

    for setup_line in setup_code:
        try:
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(setup_line))]))
        except Exception:
            try:
                parsed_stmt = cst.parse_module(setup_line).body[0]
                if isinstance(parsed_stmt, cst.SimpleStatementLine):
                    body_statements.append(parsed_stmt)
            except Exception:
                body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]))

    for teardown_line in teardown_code:
        try:
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(teardown_line))]))
        except Exception:
            try:
                parsed_stmt = cst.parse_module(teardown_line).body[0]
                if isinstance(parsed_stmt, cst.SimpleStatementLine):
                    body_statements.append(parsed_stmt)
            except Exception:
                body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

    if not body_statements:
        body_statements = [
            cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]),
            cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]),
            cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]),
        ]

    func = cst.FunctionDef(
        name=cst.Name(value="setup_method"),
        params=cst.Parameters(params=[cst.Param(name=cst.Name(value="self"), annotation=None)]),
        body=cst.IndentedBlock(body=body_statements),
        decorators=[decorator],
        returns=None,
    )

    return func


def create_teardown_fixture(teardown_code: list[str]) -> cst.FunctionDef:
    decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture")))

    body_statements = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))])]

    for teardown_line in teardown_code:
        try:
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(teardown_line))]))
        except Exception:
            try:
                parsed_stmt = cst.parse_module(teardown_line).body[0]
                if isinstance(parsed_stmt, cst.SimpleStatementLine):
                    body_statements.append(parsed_stmt)
            except Exception:
                body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

    func = cst.FunctionDef(
        name=cst.Name(value="teardown_method"),
        params=cst.Parameters(params=[cst.Param(name=cst.Name(value="self"), annotation=None)]),
        body=cst.IndentedBlock(body=body_statements),
        decorators=[decorator],
        returns=None,
    )

    return func
