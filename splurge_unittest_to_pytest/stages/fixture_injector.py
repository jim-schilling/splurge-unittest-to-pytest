"""FixtureInjector: insert fixture FunctionDef nodes into a module body.

This stage expects `fixture_nodes` in the context (list of cst.FunctionDef) and
inserts them after the pytest import if present, else after module docstring or
imports (similar to ImportInjector logic).
"""

from __future__ import annotations

from typing import Any, Optional, cast

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
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    nodes: list[cst.FunctionDef] = context.get("fixture_nodes") or []
    collector: CollectorOutput | None = context.get("collector_output")
    # Determine compat behavior. When compat is explicitly provided as False,
    # disable autouse attachment. If not provided, default to True to preserve
    # historical behavior in unit tests that call this stage directly.
    compat_val = context.get("compat", None)
    compat: bool = True if compat_val is None else bool(compat_val)
    if module is None or not nodes:
        return {"module": module}
    insert_idx = _find_insertion_index(module)
    # allow a mix of statement and small-statement/EmptyLine nodes in the new body
    new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = list(module.body)
    # Insert fixture FunctionDef nodes at the calculated insertion index.
    # For no-compat (strict pytest) output insert two blank lines before
    # each top-level def to match style expectations. For compat output
    # (where fixtures may be attached to instances) preserve the more
    # conservative single-EmptyLine separation used historically.
    for offset, fn in enumerate(nodes):
        if compat:
            # preserve older behavior: one EmptyLine after each fixture
            insert_pos = insert_idx + offset * 2
            new_body.insert(insert_pos, fn)
            if offset != len(nodes) - 1:
                new_body.insert(insert_pos + 1, cast(cst.BaseSmallStatement, cst.EmptyLine()))
        else:
            # strict/no-compat: ensure two leading EmptyLine nodes before
            # each top-level FunctionDef (this results in two blank lines
            # separating defs at module level after normalization).
            # We insert the FunctionDef followed by two EmptyLine sentinels
            # so that later formatting normalization can collapse/ensure
            # the proper counts around top-level defs.
            insert_pos = insert_idx + offset * 3
            # Insert two EmptyLine nodes before the function to yield
            # the expected two-blank-line separation at module level.
            new_body.insert(insert_pos, cast(cst.BaseSmallStatement, cst.EmptyLine()))
            new_body.insert(insert_pos, cast(cst.BaseSmallStatement, cst.EmptyLine()))
            new_body.insert(insert_pos + 2, fn)
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
        has_unittest_usage = getattr(collector, "has_unittest_usage", False)

    # Only inject autouse when either:
    #  - collector detected unittest usage, OR
    #  - compat flag was explicitly enabled (True). If compat was explicitly
    #    disabled (False), do not inject the autouse fixture even if unittest
    #    usage was detected. This allows strict pytest-style output when
    #    requested by callers.
    if has_unittest_usage and compat:
        fixture_names = [n.name.value for n in nodes]
        attach_fn = _make_autouse_attach(fixture_names)
        # Calculate where the fixtures ended. In compat mode we inserted each
        # fixture followed by an EmptyLine (except the last), so the last
        # fixture sits at insert_idx + (len(nodes)-1)*2. Insert the attach
        # sentinel after that spot. If there are no nodes, insert at
        # insert_idx.
        if nodes:
            attach_pos = insert_idx + (len(nodes) - 1) * 2 + 1
        else:
            attach_pos = insert_idx
        # insert an EmptyLine sentinel followed by the attach function
        new_body.insert(attach_pos, cast(cst.BaseSmallStatement, cst.EmptyLine()))
        new_body.insert(attach_pos + 1, attach_fn)

    new_module = module.with_changes(body=new_body)
    return {"module": new_module, "needs_pytest_import": True}
