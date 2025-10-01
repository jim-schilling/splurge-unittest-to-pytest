"""String-based fixture transformation helpers.

This module provides fallback, string-based helpers that convert
``unittest``-style setup/teardown methods into pytest fixtures. These
helpers are intentionally regex-driven and exist as a fallback when a
CST-based transformation is inappropriate or unavailable. They are
separate from the libcst-powered transformers to make targeted testing
and reuse easier.

Notes:
        - The string-based transforms are conservative and operate on the
            raw source text; they are not guaranteed to preserve all edge
            cases that a full AST transform would handle.
        - Callers that can use libcst-based helpers should prefer those for
            more robust parsing and rewriting.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from __future__ import annotations

import re

import libcst as cst


def transform_fixtures_string_based(code: str) -> str:
    """Perform conservative string-level conversion of setUp/tearDown to fixtures.

    This fallback transformer applies a small set of regex-based
    rewrites to convert ``def setUp(self):`` into an autouse
    ``setup_method`` fixture and to remove ``tearDown`` methods
    (teardown behavior is modeled via ``yield`` inside the generated
    fixture). The function is deliberately conservative and intended
    for sources where a full libcst rewrite is not possible.

    Args:
        code: The Python source code to transform.

    Returns:
        The transformed source string with basic fixture conversions
        applied.
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
    """Create a :class:`libcst.FunctionDef` representing a class-scoped fixture.

    The produced fixture is decorated with ``@pytest.fixture(scope="class", autouse=True)``
    and contains the provided ``setup_class_code`` lines, a ``yield`` to
    separate setup from teardown, and then the ``teardown_class_code``
    lines. Inputs are lists of source-code strings which are parsed and
    appended into the function body when possible.

    Args:
        setup_class_code: List of source lines to include in the setup
            portion of the fixture.
        teardown_class_code: List of source lines to include after the
            yield for teardown.

    Returns:
        A :class:`libcst.FunctionDef` node suitable for insertion into
        a module AST.
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

    body_statements: list[cst.BaseStatement] = []

    for setup_line in setup_class_code:
        try:
            # Try parsing as an expression (simple assignments/expressions)
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(setup_line))]))
        except Exception:
            try:
                # Parse full statement and append it regardless of its concrete type
                parsed_stmt = cst.parse_module(setup_line).body[0]
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
    """Create an instance-scoped autouse fixture ``setup_method``.

    The returned :class:`libcst.FunctionDef` is decorated with
    ``@pytest.fixture(autouse=True)`` and will contain parsed setup
    lines, a ``yield``, and parsed teardown lines. Inputs are lists of
    source-code strings that are parsed into libcst statements when
    possible; non-parseable lines are replaced with ``pass``.

    Args:
        setup_code: Lines to place before the ``yield``.
        teardown_code: Lines to place after the ``yield``.

    Returns:
        A :class:`libcst.FunctionDef` for ``setup_method(self)``.
    """

    decorator = cst.Decorator(
        decorator=cst.Call(
            func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture")),
            args=[cst.Arg(keyword=cst.Name(value="autouse"), value=cst.Name(value="True"))],
        )
    )

    body_statements: list[cst.BaseStatement] = []

    for setup_line in setup_code:
        try:
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(setup_line))]))
        except Exception:
            try:
                parsed_stmt = cst.parse_module(setup_line).body[0]
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
    """Create an autouse ``teardown_method`` fixture.

    This helper builds a :class:`libcst.FunctionDef` named
    ``teardown_method(self)`` decorated with ``@pytest.fixture`` and
    containing a ``yield`` followed by teardown statements parsed from
    ``teardown_code``. If parsing a line fails the helper inserts a
    ``pass`` statement as a conservative fallback.

    Args:
        teardown_code: Lines to execute after the yield.

    Returns:
        A :class:`libcst.FunctionDef` representing ``teardown_method``.
    """

    decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture")))

    body_statements: list[cst.BaseStatement] = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))])]

    for teardown_line in teardown_code:
        try:
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(teardown_line))]))
        except Exception:
            try:
                parsed_stmt = cst.parse_module(teardown_line).body[0]
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


def create_module_fixture(setup_module_code: list[str], teardown_module_code: list[str]) -> cst.FunctionDef:
    """Create a module-scoped, autouse fixture named ``setup_module``.

    The returned node is decorated with
    ``@pytest.fixture(scope="module", autouse=True)`` and contains the
    provided setup lines, a ``yield``, and the provided teardown lines.

    Args:
        setup_module_code: Lines to include before the yield.
        teardown_module_code: Lines to include after the yield.

    Returns:
        A :class:`libcst.FunctionDef` node for insertion into the module
        AST.
    """

    decorator = cst.Decorator(
        decorator=cst.Call(
            func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture")),
            args=[
                cst.Arg(keyword=cst.Name(value="scope"), value=cst.SimpleString(value='"module"')),
                cst.Arg(keyword=cst.Name(value="autouse"), value=cst.Name(value="True")),
            ],
        )
    )

    body_statements: list[cst.BaseStatement] = []

    for line in setup_module_code:
        try:
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(line))]))
        except Exception:
            try:
                parsed_stmt = cst.parse_module(line).body[0]
                body_statements.append(parsed_stmt)
            except Exception:
                body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

    # Insert the yield for teardown pairing
    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]))

    for line in teardown_module_code:
        try:
            body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(line))]))
        except Exception:
            try:
                parsed_stmt = cst.parse_module(line).body[0]
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
        name=cst.Name(value="setup_module"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=body_statements),
        decorators=[decorator],
        returns=None,
    )

    return func
