"""Fixture helper creators extracted from the monolithic converter.

These functions are pure-ish: they accept the needed inputs and return libcst
nodes. The class in `converter.py` keeps thin wrappers that manage transformer
state (e.g., setting self.needs_pytest_import) and call these helpers.
"""
from typing import Any, List

import libcst as cst

__all__: List[str] = [
    "create_fixture_with_cleanup",
    "create_simple_fixture",
    "parse_setup_assignments",
]

from .setup_parser import parse_setup_assignments


def create_fixture_with_cleanup(attr_name: str, value_expr: cst.BaseExpression, cleanup_statements: List[cst.BaseStatement]) -> cst.FunctionDef:
    """Create a fixture with yield pattern and cleanup.

    This mirrors the logic previously inside UnittestToPytestTransformer._create_fixture_with_cleanup.
    """
    fixture_decorator = cst.Decorator(
        decorator=cst.Call(
            func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture"))
        )
    )

    simple_types = (cst.Integer, cst.Float, cst.SimpleString)
    if isinstance(value_expr, simple_types):
        yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=value_expr))])
        body = cst.IndentedBlock(body=[yield_stmt] + cleanup_statements)
    else:
        value_name = f"_{attr_name}_value"
        value_assign = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(value_name))],
                    value=value_expr,
                )
            ]
        )
        yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=cst.Name(value_name)))])

    # Replace references to attr_name within cleanup_statements with the local value_name
    from .name_replacer import replace_names_in_statements

    safe_cleanup = replace_names_in_statements(cleanup_statements, attr_name, value_name)

    body = cst.IndentedBlock(body=[value_assign, yield_stmt] + safe_cleanup)

    fixture_func = cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(),
        body=body,
        decorators=[fixture_decorator],
        returns=None,
        asynchronous=None,
    )

    return fixture_func


def create_simple_fixture(attr_name: str, value_expr: cst.BaseExpression) -> cst.FunctionDef:
    """Create a simple fixture with return (no cleanup needed)."""
    fixture_decorator = cst.Decorator(
        decorator=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
    )

    value_name = f"_{attr_name}_value"
    value_assign = cst.SimpleStatementLine(body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name(value_name))], value=value_expr)])
    return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=cst.Name(value_name))])
    body = cst.IndentedBlock(body=[value_assign, return_stmt])

    fixture_func = cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(),
        body=body,
        decorators=[fixture_decorator],
        returns=None,
        asynchronous=None,
    )

    return fixture_func


def make_autouse_attach_to_instance_fixture(setup_fixtures: dict[str, cst.FunctionDef]) -> cst.FunctionDef:
    """Create an autouse fixture function that attaches named fixtures to unittest-style test instances.

    Returns a libcst.FunctionDef for:
        @pytest.fixture(autouse=True)
        def _attach_to_instance(request):
            inst = getattr(request, 'instance', None)
            if inst is not None:
                setattr(inst, 'name', name)  # for each fixture name
    """
    # Build inst = getattr(request, 'instance', None)
    inst_assign = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("inst"))],
                value=cst.Call(func=cst.Name("getattr"), args=[
                    cst.Arg(value=cst.Name("request")),
                    cst.Arg(value=cst.SimpleString("'instance'")),
                    cst.Arg(value=cst.Name("None")),
                ]),
            )
        ]
    )

    set_calls: list[cst.BaseStatement] = []
    for name in setup_fixtures.keys():
        set_calls.append(
            cst.SimpleStatementLine(
                body=[
                    cst.Expr(
                        value=cst.Call(
                            func=cst.Name("setattr"),
                            args=[
                                cst.Arg(value=cst.Name("inst")),
                                cst.Arg(value=cst.SimpleString(f"'{name}'")),
                                cst.Arg(value=cst.Name(name)),
                            ],
                        )
                    )
                ]
            )
        )

    if_block = cst.IndentedBlock(body=set_calls)
    if_stmt = cst.If(test=cst.Comparison(left=cst.Name("inst"), comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))]), body=if_block)

    decorator = cst.Decorator(
        decorator=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")), args=[
            cst.Arg(keyword=cst.Name("autouse"), value=cst.Name("True"))
        ])
    )

    func = cst.FunctionDef(
        name=cst.Name("_attach_to_instance"),
        params=cst.Parameters(params=[cst.Param(name=cst.Name("request"))]),
        body=cst.IndentedBlock(body=[inst_assign, if_stmt]),
        decorators=[decorator],
    )

    return func


def add_autouse_attach_fixture_to_module(module_node: cst.Module, setup_fixtures: dict[str, cst.FunctionDef]) -> cst.Module:
    """Insert the autouse attachment fixture into the module (after pytest import if present)."""
    if not setup_fixtures:
        return module_node

    func = make_autouse_attach_to_instance_fixture(setup_fixtures)

    new_body: list[Any] = list(module_node.body)
    insert_pos = 0
    for i, stmt in enumerate(new_body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.Import):
                for alias in first.names:
                    if isinstance(alias.name, cst.Name) and alias.name.value == "pytest":
                        insert_pos = i + 1
                        break
            if insert_pos:
                break

    new_body.insert(insert_pos, cst.EmptyLine())
    new_body.insert(insert_pos + 1, func)

    return module_node.with_changes(body=new_body)


def create_fixture_for_attribute(attr_name: str, value_expr: cst.BaseExpression, teardown_cleanup: dict[str, list[cst.BaseStatement]]) -> cst.FunctionDef:
    """Create fixture for attribute (delegates to cleanup/simple creators)."""
    cleanup_statements = teardown_cleanup.get(attr_name, [])
    if cleanup_statements:
        return create_fixture_with_cleanup(attr_name, value_expr, cleanup_statements)
    return create_simple_fixture(attr_name, value_expr)
