"""Insert generated pytest fixture function nodes into a module.

Place generated fixture functions deterministically after imports (or
the module docstring) and signal via the returned context that a
``pytest`` import is required. Fixtures are emitted with stable spacing
markers so later formatting yields predictable output.

Publics:
    fixture_injector_stage

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Optional, cast
from ..types import PipelineContext

import libcst as cst
from .events import EventBus, TaskStarted, TaskCompleted, TaskErrored
from .fixture_injector_tasks import InsertFixtureNodesTask

DOMAINS = ["stages", "fixtures"]

# Associated domains for this module


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


def _find_insertion_index(module: cst.Module) -> int:
    """Find deterministic insertion index for fixture nodes.

    Prefer an existing `import pytest` line; otherwise place after a
    module docstring and existing imports.
    """
    for idx, stmt in enumerate(module.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            expr = stmt.body[0]
            if isinstance(expr, cst.Import):
                for name in expr.names:
                    if getattr(name.name, "value", None) == "pytest":
                        return idx + 1

    start_idx = 0
    if module.body:
        first = module.body[0]
        if (
            isinstance(first, cst.SimpleStatementLine)
            and first.body
            and isinstance(first.body[0], cst.Expr)
            and isinstance(first.body[0].value, cst.SimpleString)
        ):
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
        break
    return insert_idx


def fixture_injector_stage(context: PipelineContext) -> PipelineContext:
    """Insert generated fixture functions into ``module`` via a task."""
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is None:
        return cast(PipelineContext, {"module": module})
    stage_id = "stages.fixture_injector"
    bus = context.get("__event_bus__")
    task = InsertFixtureNodesTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=task.id))
        res = task.execute(context, resources=None)
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=task.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=task.id, error=exc))
        return cast(PipelineContext, {"module": module})
    return cast(PipelineContext, res.delta.values)
