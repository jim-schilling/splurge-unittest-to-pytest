"""Focused Steps for the raises_stage: Parse -> Transform -> Normalize Attrs

Each Step returns a StepResult and does not mutate the input context in-place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import libcst as cst

from ..types import ContextDelta, StepResult
from .raises_stage import ExceptionAttrRewriter, RaisesRewriter

DOMAINS = ["stages", "raises", "steps"]


@dataclass
class ParseRaisesStep:
    id: str = "steps.raises.parse"
    name: str = "parse_module"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}), skipped=True)
        return StepResult(delta=ContextDelta(values={"module": mod}))


@dataclass
class TransformRaisesStep:
    id: str = "steps.raises.transform"
    name: str = "transform_raises"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}), skipped=True)
        transformer = RaisesRewriter()
        try:
            new_mod = mod.visit(transformer)
        except Exception as exc:  # pragma: no cover - defensive
            return StepResult(delta=ContextDelta(values={"module": mod}), errors=[exc])
        return StepResult(
            delta=ContextDelta(
                values={
                    "module": new_mod,
                    "needs_pytest_import": bool(getattr(transformer, "made_changes", False)),
                }
            )
        )


@dataclass
class NormalizeExceptionAttrStep:
    id: str = "steps.raises.normalize_exception_attr"
    name: str = "normalize_exception_attr"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}), skipped=True)

        class _WithCollector(cst.CSTVisitor):
            def __init__(self) -> None:
                self.names: set[str] = set()

            def visit_With(self, node: cst.With) -> None:
                try:
                    items = node.items or []
                    if not items:
                        return None
                    first = items[0]
                    call = first.item
                    if isinstance(call, cst.Call) and isinstance(call.func, cst.Attribute):
                        func = call.func
                        if (
                            isinstance(func.value, cst.Name)
                            and func.value.value == "pytest"
                            and isinstance(func.attr, cst.Name)
                            and func.attr.value == "raises"
                        ):
                            asname = first.asname
                            if asname and isinstance(asname.name, cst.Name):
                                self.names.add(asname.name.value)
                except Exception:
                    pass

        collector = _WithCollector()
        mod.visit(collector)
        new_mod = mod
        try:
            for name in sorted(collector.names):
                if name:
                    new_mod = new_mod.visit(ExceptionAttrRewriter(name))
        except Exception as exc:  # pragma: no cover - defensive
            return StepResult(delta=ContextDelta(values={"module": mod}), errors=[exc])

        return StepResult(delta=ContextDelta(values={"module": new_mod}))


__all__ = ["ParseRaisesStep", "TransformRaisesStep", "NormalizeExceptionAttrStep"]
