"""FixtureGenerator stage: produce FixtureSpec entries and cst.FunctionDef fixture nodes
from CollectorOutput.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput
from libcst import matchers as m


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
    used_local_names: set[str] = set()
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
            # determine local name and ensure uniqueness
            base_local = f"_{attr}_value"
            local_name = base_local
            suffix = 1
            while local_name in used_local_names:
                suffix += 1
                local_name = f"{base_local}_{suffix}"
            used_local_names.add(local_name)
            spec.local_value_name = local_name

            # bind value to local variable in all cases to make cleanup rewriting consistent
            assign = cst.SimpleStatementLine(body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name(local_name))], value=value)])

            # helper rewriter to replace self.attr or cls.attr with local_name
            class _AttrRewriter(cst.CSTTransformer):
                def __init__(self, target_attr: str, local: str) -> None:
                    self.target_attr = target_attr
                    self.local = local

                def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
                    if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
                        if isinstance(original.attr, cst.Name) and original.attr.value == self.target_attr:
                            return cst.Name(self.local)
                    return updated

            # body: return or yield
            if yield_style:
                # yield the local name
                yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(cst.Name(local_name)))])
                # transform cleanup statements to reference the local name instead of self.attr
                body_stmts = [assign, yield_stmt]
                for stmt in spec.cleanup_statements:
                    new_stmt = stmt.visit(_AttrRewriter(attr, local_name))
                    body_stmts.append(new_stmt)
                body = cst.IndentedBlock(body=body_stmts)
                func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                fixture_nodes.append(func)
            else:
                # non-yield: return the local name
                return_stmt = cst.SimpleStatementLine(body=[cst.Return(cst.Name(local_name))])
                body = cst.IndentedBlock(body=[assign, return_stmt])
                func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                fixture_nodes.append(func)
    return {"fixture_specs": specs, "fixture_nodes": fixture_nodes}
