"""Tidy stage: insert EmptyLine separators between top-level fixtures and classes for readability."""
from __future__ import annotations

from typing import Any, Dict, List

import libcst as cst


def tidy_stage(context: Dict[str, Any]) -> Dict[str, Any]:
    module: cst.Module = context.get("module")
    if module is None:
        return {"module": module}
    new_body: List[cst.BaseStatement] = []
    prev_was_fixture = False
    for stmt in module.body:
        is_fixture = isinstance(stmt, cst.FunctionDef) and any(
            isinstance(d.decorator, cst.Attribute) and d.decorator.attr.value == "fixture" for d in getattr(stmt, "decorators", [])
        )
        if prev_was_fixture and not is_fixture:
            # insert an empty line separation
            new_body.append(cst.EmptyLine())
        new_body.append(stmt)
        prev_was_fixture = is_fixture
    new_module = module.with_changes(body=new_body)
    # Ensure test methods inside classes have a 'self' parameter when missing
    class EnsureSelfParam(cst.CSTTransformer):
        def __init__(self) -> None:
            super().__init__()
            self._in_class = False

        def visit_ClassDef(self, node: cst.ClassDef) -> None:
            self._in_class = True

        def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
            self._in_class = False
            return updated_node

        def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
            if not self._in_class:
                return updated_node
            if not original_node.name.value.startswith("test"):
                return updated_node
            # if no params, add 'self'
            if not updated_node.params.params:
                new_params = [cst.Param(name=cst.Name("self"))]
                return updated_node.with_changes(params=updated_node.params.with_changes(params=new_params))
            return updated_node

    final_module = new_module.visit(EnsureSelfParam())
    return {"module": final_module}
