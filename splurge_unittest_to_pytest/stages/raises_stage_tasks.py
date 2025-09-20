"""CstTask units for raises_stage (Stage-4 decomposition).

Tasks:
  - RewriteRaisesTask: apply RaisesRewriter
  - NormalizeExceptionAttrTask: run ExceptionAttrRewriter over collected names in module
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, TYPE_CHECKING

import libcst as cst

from ..types import Task, TaskResult, ContextDelta

if TYPE_CHECKING:
    from ..types import Step
from .raises_stage import RaisesRewriter, ExceptionAttrRewriter


DOMAINS = ["stages", "raises", "tasks"]


@dataclass
class RewriteRaisesTask(Task):
    id: str = "tasks.raises.rewrite_raises"
    name: str = "rewrite_raises"
    steps: Sequence["Step"] = ()

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return TaskResult(delta=ContextDelta(values={}))
        transformer = RaisesRewriter()
        new_mod = mod.visit(transformer)
        return TaskResult(
            delta=ContextDelta(
                values={
                    "module": new_mod,
                    # surface whether pytest.raises constructs were created
                    "needs_pytest_import": bool(getattr(transformer, "made_changes", False)),
                }
            )
        )


@dataclass
class NormalizeExceptionAttrTask(Task):
    id: str = "tasks.raises.normalize_exception_attr"
    name: str = "normalize_exception_attr"
    steps: Sequence["Step"] = ()

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        maybe_module = context.get("module")
        module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
        if module is None:
            return TaskResult(delta=ContextDelta(values={}))

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
        module.visit(collector)
        new_mod = module
        try:
            for name in sorted(collector.names):
                if name:
                    new_mod = new_mod.visit(ExceptionAttrRewriter(name))
        except Exception:
            return TaskResult(delta=ContextDelta(values={"module": module}))
        return TaskResult(delta=ContextDelta(values={"module": new_mod}))


__all__ = ["RewriteRaisesTask", "NormalizeExceptionAttrTask"]
