"""Insert generated pytest fixture FunctionDef nodes into a module.

The stage places generated fixture functions deterministically after
imports (or the module docstring) and signals via the context that a
``pytest`` import is required. Fixtures are emitted with stable
spacing markers so later formatting produces predictable output.
"""

from __future__ import annotations

from typing import Any, Optional, cast

import libcst as cst

DOMAINS = ["stages", "fixtures"]

# Associated domains for this module


def _find_insertion_index(module: cst.Module) -> int:
    # prefer after pytest import
    for idx, stmt in enumerate(module.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            expr = stmt.body[0]
            if isinstance(expr, cst.Import):
                for name in expr.names:
                    if name.name.value == "pytest":
                        return idx + 1
    # Find the first index after any leading imports (and optional
    # module docstring). This ensures fixtures are placed after the
    # import block even if import nodes are represented in varying ways.
    start_idx = 0
    if module.body:
        first = module.body[0]
        if (
            isinstance(first, cst.SimpleStatementLine)
            and first.body
            and isinstance(first.body[0], cst.Expr)
            and isinstance(first.body[0].value, cst.SimpleString)
        ):
            # skip docstring
            start_idx = 1

    insert_idx = start_idx
    for idx in range(start_idx, len(module.body)):
        stmt = module.body[idx]
        if (
            isinstance(stmt, cst.SimpleStatementLine)
            and stmt.body
            and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
        ):
            insert_idx = idx + 1
            continue
        # stop at first non-import statement
        break

    return insert_idx


def _make_autouse_attach(fixture_names: list[str]) -> cst.FunctionDef:
    # create a fixture that attaches results onto request.instance
    # def _attach_to_instance(request):
    #     inst = getattr(request, "instance", None)
    #     if inst is not None:
    #         inst.attr = var
    #     return None
    body: list[cst.BaseStatement] = []
    # inst = getattr(request, 'instance', None)
    assign = cst.SimpleStatementLine(
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
    if_stmt = cst.If(
        test=cst.Comparison(
            left=cst.Name("inst"), comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))]
        ),
        body=cst.IndentedBlock(body=inner),
    )
    body.append(if_stmt)
    body.append(cst.SimpleStatementLine(body=[cst.Return(cst.Name("None"))]))
    # make the autouse fixture accept only `request` and use
    # request.getfixturevalue(...) to retrieve fixture values.
    params_list: list[cst.Param] = [cst.Param(name=cst.Name("request"))]
    params = cst.Parameters(params=params_list)
    # decorator @pytest.fixture(autouse=True)
    decorator = cst.Decorator(
        decorator=cst.Call(
            func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")),
            args=[cst.Arg(keyword=cst.Name("autouse"), value=cst.Name("True"))],
        )
    )
    func = cst.FunctionDef(
        name=cst.Name("_attach_to_instance"), params=params, body=cst.IndentedBlock(body=body), decorators=[decorator]
    )
    return func


def fixture_injector_stage(context: dict[str, Any]) -> dict[str, Any]:
    """Insert generated fixture functions into ``module``.

    The stage will insert two empty-line sentinels before each top-level
    fixture to ensure canonical spacing. It returns a mapping containing the
    possibly-updated ``module`` and signals that ``pytest`` import is needed
    via the ``needs_pytest_import`` key.
    """

    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    nodes: list[cst.FunctionDef] = context.get("fixture_nodes") or []
    # Compatibility mode has been removed; this stage now always emits
    # strict pytest-style fixtures. Insert two EmptyLine sentinels before
    # each top-level fixture to ensure canonical spacing after formatting.
    if module is None or not nodes:
        return {"module": module}
    insert_idx = _find_insertion_index(module)
    # allow a mix of statement and small-statement/EmptyLine nodes in the new body
    new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = list(module.body)
    # Insert fixture FunctionDef nodes at the calculated insertion index.
    # Always emit strict/no-compat spacing: insert two EmptyLine sentinels
    # before each top-level fixture so the module normalizer produces two
    # blank lines between top-level defs.
    for offset, fn in enumerate(nodes):
        insert_pos = insert_idx + offset * 3
        # Insert two EmptyLine sentinels followed by the FunctionDef
        new_body.insert(insert_pos, cast(cst.BaseSmallStatement, cst.EmptyLine()))
        new_body.insert(insert_pos, cast(cst.BaseSmallStatement, cst.EmptyLine()))
        new_body.insert(insert_pos + 2, fn)
    # Insert fixtures into module body. Autouse attach fixtures and class
    # preserving behavior have been removed; generated fixtures are intended
    # to be used directly by top-level test wrappers. Signal that pytest
    # import is needed so ImportInjector will insert it.
    # Normalize spacing: ensure exactly two EmptyLine nodes before each
    # top-level FunctionDef or ClassDef. Collapse runs longer than two.
    normalized: list[cst.BaseStatement | cst.BaseSmallStatement] = []
    i = 0
    while i < len(new_body):
        node = new_body[i]
        if isinstance(node, (cst.FunctionDef, cst.ClassDef)):
            # count trailing empties in normalized so far
            # remove trailing EmptyLines to avoid accumulating more than needed
            while normalized and isinstance(normalized[-1], cst.EmptyLine):
                normalized.pop()
            # append two EmptyLine sentinels before the top-level def
            normalized.append(cast(cst.BaseSmallStatement, cst.EmptyLine()))
            normalized.append(cast(cst.BaseSmallStatement, cst.EmptyLine()))
            normalized.append(node)
            i += 1
            continue
        # preserve existing empties and other nodes
        normalized.append(node)
        i += 1

    new_module = module.with_changes(body=normalized)
    return {"module": new_module, "needs_pytest_import": True}
