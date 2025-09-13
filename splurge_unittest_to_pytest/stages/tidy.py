"""Tidy stage: central spacing and light post-processing.

This stage delegates spacing normalization to the shared
`formatting.normalize_module` helper (ensures import grouping, dedup,
and consistent blank-line counts). It also ensures class test methods
have a `self` parameter when appropriate.
"""

from __future__ import annotations

from typing import Any, Optional

import libcst as cst

from splurge_unittest_to_pytest.stages.formatting import normalize_module


def tidy_stage(context: dict[str, Any]) -> dict[str, Any]:
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is None:
        return {"module": module}

    # Centralized formatting pass
    normalized = normalize_module(module)

    # Ensure class test methods have a 'self' parameter when missing
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
            if not updated_node.params.params:
                new_params = [cst.Param(name=cst.Name("self"))]
                return updated_node.with_changes(params=updated_node.params.with_changes(params=new_params))
            return updated_node

    final_module = normalized.visit(EnsureSelfParam())
    return {"module": final_module}
