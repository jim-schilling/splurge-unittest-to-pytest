"""Tidy stage: insert EmptyLine separators between top-level fixtures and classes for readability."""
from __future__ import annotations

from typing import Any, Optional, cast

import libcst as cst


def tidy_stage(context: dict[str, Any]) -> dict[str, Any]:
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is None:
        return {"module": module}
    # allow insertion of EmptyLine (a BaseSmallStatement) into the module body
    new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
    prev_was_fixture = False
    for stmt in module.body:
        is_fixture = isinstance(stmt, cst.FunctionDef) and any(
            isinstance(d.decorator, cst.Attribute) and d.decorator.attr.value == "fixture" for d in getattr(stmt, "decorators", [])
        )
        if prev_was_fixture and not is_fixture:
            # insert an empty line separation, but avoid duplicate EmptyLines
                    if not new_body or not isinstance(new_body[-1], cst.EmptyLine):
                        new_body.append(cast(cst.BaseSmallStatement, cst.EmptyLine()))
        new_body.append(cast(cst.BaseStatement | cst.BaseSmallStatement, stmt))
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
