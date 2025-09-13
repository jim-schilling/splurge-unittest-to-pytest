"""Helpers to build and insert the autouse attachment fixture for unittest compatibility."""

from typing import Any

import libcst as cst


def build_attach_to_instance_fixture(setup_fixtures: dict[str, cst.FunctionDef]) -> cst.FunctionDef:
    """Construct the `_attach_to_instance` fixture function node.

    Args:
        setup_fixtures: Mapping of fixture names to their FunctionDef nodes.

    Returns:
        A libcst.FunctionDef node representing the autouse fixture.
    """
    # Build function body: inst = getattr(request, 'instance', None)
    inst_assign = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("inst"))],
                value=cst.Call(
                    func=cst.Name("getattr"),
                    args=[
                        cst.Arg(value=cst.Name("request")),
                        cst.Arg(value=cst.SimpleString("'instance'")),
                        cst.Arg(value=cst.Name("None")),
                    ],
                ),
            )
        ]
    )

    # Build setattr calls under if inst is truthy.
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
    if_stmt = cst.If(
        test=cst.Comparison(
            left=cst.Name("inst"), comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))]
        ),
        body=if_block,
    )

    decorator = cst.Decorator(
        decorator=cst.Call(
            func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")),
            args=[cst.Arg(keyword=cst.Name("autouse"), value=cst.Name("True"))],
        )
    )

    func = cst.FunctionDef(
        name=cst.Name("_attach_to_instance"),
        params=cst.Parameters(params=[cst.Param(name=cst.Name("request"))]),
        body=cst.IndentedBlock(body=[inst_assign, if_stmt]),
        decorators=[decorator],
    )

    return func


def insert_attach_fixture_into_module(module_node: cst.Module, fixture_func: cst.FunctionDef) -> cst.Module:
    """Insert the autouse fixture function into the module body near pytest import.

    Returns a new Module node with the fixture inserted.
    """
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
    new_body.insert(insert_pos + 1, fixture_func)

    return module_node.with_changes(body=new_body)
