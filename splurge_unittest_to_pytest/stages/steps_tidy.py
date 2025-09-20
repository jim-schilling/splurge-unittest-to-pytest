from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, cast

import libcst as cst

from ..types import Step, StepResult, ContextDelta
from .formatting import normalize_module

DOMAINS = ["stages", "tidy", "steps"]


def _get_module(context: Mapping[str, Any]) -> cst.Module | None:
    mod = context.get("module")
    return mod if isinstance(mod, cst.Module) else None


@dataclass
class NormalizeSpacingStep(Step):
    id: str = "steps.tidy.normalize_spacing"
    name: str = "normalize_spacing"

    def execute(self, ctx: Mapping[str, Any], resources: Any) -> StepResult:
        mod = _get_module(ctx)
        if mod is None:
            return StepResult(delta=ContextDelta(values={}))
        normalized = normalize_module(mod)
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
        new_mod = normalized.with_changes(body=final_body)
        return StepResult(delta=ContextDelta(values={"module": new_mod}))


@dataclass
class EnsureSelfParamStep(Step):
    id: str = "steps.tidy.ensure_self_param"
    name: str = "ensure_self_param"

    def execute(self, ctx: Mapping[str, Any], resources: Any) -> StepResult:
        mod = _get_module(ctx)
        if mod is None:
            return StepResult(delta=ContextDelta(values={}))

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

        final_module = mod.visit(EnsureSelfParam())
        return StepResult(delta=ContextDelta(values={"module": final_module}))


__all__ = ["NormalizeSpacingStep", "EnsureSelfParamStep"]
