"""FixtureInjector: insert fixture FunctionDef nodes into a module body.

This stage expects `fixture_nodes` in the context (list of cst.FunctionDef) and
inserts them after the pytest import if present, else after module docstring or
imports (similar to ImportInjector logic).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


def _find_insertion_index(module: cst.Module) -> int:
    # prefer after pytest import
    for idx, stmt in enumerate(module.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            expr = stmt.body[0]
            if isinstance(expr, cst.Import):
                for name in expr.names:
                    if name.name.value == "pytest":
                        return idx + 1
    # else after docstring
    for idx, stmt in enumerate(module.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body and isinstance(stmt.body[0], cst.Expr) and isinstance(stmt.body[0].value, cst.SimpleString):
            return idx + 1
    # else after last import
    last_import = -1
    for idx, stmt in enumerate(module.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom)):
            last_import = idx
    if last_import >= 0:
        return last_import + 1
    return 0


def _make_autouse_attach(fixture_names: list[str]) -> cst.FunctionDef:
    # create a fixture that attaches results onto request.instance
    # def _attach_to_instance(request):
    #     inst = getattr(request, "instance", None)
    #     if inst is not None:
    #         inst.attr = var
    #     return None
    body: list[cst.BaseStatement] = []
    # inst = getattr(request, 'instance', None)
    assign = cst.SimpleStatementLine(body=[
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
    ])
    body.append(assign)
    # if inst is not None: attach
    inner: list[cst.BaseStatement] = []
    for name in fixture_names:
        # setattr(inst, 'name', name)
        attr_assign = cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    value=cst.Call(
                        func=cst.Name("setattr"),
                        args=[
                            cst.Arg(value=cst.Name("inst")),
                            cst.Arg(value=cst.SimpleString(f"'{name}'")),
                            # use request.getfixturevalue('<name>') to deterministically
                            # retrieve the fixture value instead of relying on
                            # pytest to inject it as a parameter to the autouse
                            # function.
                            cst.Arg(
                                value=cst.Call(
                                    func=cst.Attribute(value=cst.Name("request"), attr=cst.Name("getfixturevalue")),
                                    args=[cst.Arg(value=cst.SimpleString(f"'{name}'"))],
                                )
                            ),
                        ],
                    )
                )
            ]
        )
        inner.append(attr_assign)
    if_stmt = cst.If(test=cst.Comparison(left=cst.Name("inst"), comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))]), body=cst.IndentedBlock(body=inner))
    body.append(if_stmt)
    body.append(cst.SimpleStatementLine(body=[cst.Return(cst.Name("None"))]))
    # make the autouse fixture accept only `request` and use
    # request.getfixturevalue(...) to retrieve fixture values.
    params_list: list[cst.Param] = [cst.Param(name=cst.Name("request"))]
    params = cst.Parameters(params=params_list)
    # decorator @pytest.fixture(autouse=True)
    decorator = cst.Decorator(
        decorator=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")), args=[cst.Arg(keyword=cst.Name("autouse"), value=cst.Name("True"))])
    )
    func = cst.FunctionDef(name=cst.Name("_attach_to_instance"), params=params, body=cst.IndentedBlock(body=body), decorators=[decorator])
    return func


def fixture_injector_stage(context: dict[str, Any]) -> dict[str, Any]:
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    nodes: list[cst.FunctionDef] = context.get("fixture_nodes") or []
    collector: CollectorOutput | None = context.get("collector_output")
    compat: bool = context.get("compat", False)
    if module is None or not nodes:
        return {"module": module}
    insert_idx = _find_insertion_index(module)
    new_body = list(module.body)
    # insert an empty line then fixtures
    for i, fn in enumerate(nodes):
        new_body.insert(insert_idx + i, fn)
    # Insert fixtures into module body. We do not add an autouse attach
    # fixture here; instead the fixtures are intended to be used as normal
    # pytest fixtures by generated top-level test wrappers (created in the
    # fixtures stage). Signal that pytest import is needed so ImportInjector
    # will insert it.
    # If the original module used unittest TestCase classes (or compat mode
    # is requested), add an autouse attach fixture that will attach fixture
    # values onto test instances during pytest runs. This keeps converted
    # modules runnable while allowing pytest to inject fixtures.
    has_unittest_usage = False
    if collector is not None:
        has_unittest_usage = getattr(collector, 'has_unittest_usage', False)

    if has_unittest_usage or compat:
        fixture_names = [n.name.value for n in nodes]
        attach_fn = _make_autouse_attach(fixture_names)
        new_body.insert(insert_idx + len(nodes), cst.EmptyLine())
        new_body.insert(insert_idx + len(nodes) + 1, attach_fn)

    new_module = module.with_changes(body=new_body)
    return {"module": new_module, "needs_pytest_import": True}
