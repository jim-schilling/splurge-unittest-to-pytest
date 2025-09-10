"""FixtureGenerator stage: produce FixtureSpec entries and cst.FunctionDef fixture nodes
from CollectorOutput.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


@dataclass
class FixtureSpec:
    name: str
    value_expr: cst.BaseExpression
    cleanup_statements: List[cst.BaseStatement]
    yield_style: bool
    local_value_name: Optional[str] = None


def _is_literal(expr: cst.BaseExpression) -> bool:
    return isinstance(expr, (cst.Integer, cst.Float, cst.SimpleString, cst.Name))


def generator_stage(context: dict) -> dict:
    out: CollectorOutput = context.get("collector_output")
    if out is None:
        return {}
    specs: Dict[str, FixtureSpec] = {}
    fixture_nodes: List[cst.FunctionDef] = []
    for cls_name, cls in out.classes.items():
        for attr, value in cls.setup_assignments.items():
            # simple heuristic: if any teardown statements exist, treat as yield-style
            has_cleanup = bool(cls.teardown_statements)
            yield_style = has_cleanup
            fname = f"{attr}"
            spec = FixtureSpec(name=fname, value_expr=value, cleanup_statements=cls.teardown_statements.copy(), yield_style=yield_style)
            specs[fname] = spec
            # create a minimal fixture node: @pytest.fixture
            decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
            # body: return or yield
            if yield_style:
                # if literal, yield directly
                if _is_literal(value):
                    body_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(value))])
                else:
                    # bind to local variable then yield it
                    local_name = f"_{attr}_value"
                    spec.local_value_name = local_name
                    assign = cst.SimpleStatementLine(body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name(local_name))], value=value)])
                    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(cst.Name(local_name)))])
                    body = cst.IndentedBlock(body=[assign, yield_stmt])
                    func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                    fixture_nodes.append(func)
                    continue
            else:
                if _is_literal(value):
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(value)])
                else:
                    local_name = f"_{attr}_value"
                    spec.local_value_name = local_name
                    assign = cst.SimpleStatementLine(body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name(local_name))], value=value)])
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(cst.Name(local_name))])
                    body = cst.IndentedBlock(body=[assign, return_stmt])
                    func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                    fixture_nodes.append(func)
                    continue
            # yield direct literal case
            if yield_style and _is_literal(value):
                body = cst.IndentedBlock(body=[body_stmt])
                func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                fixture_nodes.append(func)
            elif not yield_style and _is_literal(value):
                body = cst.IndentedBlock(body=[return_stmt])
                func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                fixture_nodes.append(func)
    return {"fixture_specs": specs, "fixture_nodes": fixture_nodes}
