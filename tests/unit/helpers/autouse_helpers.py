import libcst as cst

from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator


def make_autouse_attach(setup_fixtures: dict[str, cst.FunctionDef]) -> cst.FunctionDef:
    """Create an autouse attach fixture FunctionDef for tests to reuse.

    This is a test-only helper to replace duplicated local helpers across tests.
    """
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

    decorator = build_pytest_fixture_decorator({"autouse": True})

    func = cst.FunctionDef(
        name=cst.Name("_attach_to_instance"),
        params=cst.Parameters(params=[cst.Param(name=cst.Name("request"))]),
        body=cst.IndentedBlock(body=[inst_assign, if_stmt]),
        decorators=[decorator],
    )

    return func


def insert_attach_fixture_into_module(module_node: cst.Module, fixture_func: cst.FunctionDef) -> cst.Module:
    """Insert fixture_func into module_node after pytest import (if present).

    Returns a new Module node with the fixture inserted.
    """
    new_body: list = list(module_node.body)
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
