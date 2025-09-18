"""CstTask units for tidy stage.

Tasks:
  - NormalizeSpacingTask: ensure two EmptyLines before top-level defs/classes
  - EnsureSelfParamTask: add self param to class test methods missing params
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, cast

import libcst as cst

from ..types import Task, TaskResult, ContextDelta
from .formatting import normalize_module


DOMAINS = ["stages", "tidy", "tasks"]


@dataclass
class NormalizeSpacingTask(Task):
    id: str = "tasks.tidy.normalize_spacing"
    name: str = "normalize_spacing"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        maybe_module = context.get("module")
        module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
        if module is None:
            return TaskResult(delta=ContextDelta(values={"module": module}))
        normalized = normalize_module(module)
        final_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
        for node in list(normalized.body):
            if isinstance(node, (cst.FunctionDef, cst.ClassDef)):
                while final_body and isinstance(final_body[-1], cst.EmptyLine):
                    final_body.pop()
                final_body.append(cast(cst.BaseSmallStatement, cst.EmptyLine()))
                final_body.append(cast(cst.BaseSmallStatement, cst.EmptyLine()))
                final_body.append(node)
                continue
            final_body.append(node)
        normalized = normalized.with_changes(body=final_body)
        return TaskResult(delta=ContextDelta(values={"module": normalized}))


@dataclass
class EnsureSelfParamTask(Task):
    id: str = "tasks.tidy.ensure_self_param"
    name: str = "ensure_self_param"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        maybe_module = context.get("module")
        module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
        if module is None:
            return TaskResult(delta=ContextDelta(values={"module": module}))

        class EnsureSelfParam(cst.CSTTransformer):
            def __init__(self) -> None:
                super().__init__()
                self._in_class = False

            def visit_ClassDef(self, node: cst.ClassDef) -> None:
                self._in_class = True

            def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
                self._in_class = False
                return updated_node

            def leave_FunctionDef(
                self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
            ) -> cst.FunctionDef:
                if not self._in_class:
                    return updated_node
                if not original_node.name.value.startswith("test"):
                    return updated_node
                if not updated_node.params.params:
                    new_params = [cst.Param(name=cst.Name("self"))]
                    return updated_node.with_changes(params=updated_node.params.with_changes(params=new_params))
                return updated_node

        final_module = module.visit(EnsureSelfParam())
        return TaskResult(delta=ContextDelta(values={"module": final_module}))


__all__ = ["NormalizeSpacingTask", "EnsureSelfParamTask"]
