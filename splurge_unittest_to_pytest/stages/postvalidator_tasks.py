"""Task for postvalidator stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import libcst as cst

from ..types import ContextDelta, Task, TaskResult

DOMAINS = ["stages", "validation", "tasks"]


@dataclass
class ValidateModuleTask(Task):
    id: str = "tasks.validation.validate_module"
    name: str = "validate_module"
    # Expose steps per Task protocol; this task performs work directly so
    # it exposes an empty sequence of steps for introspection.
    if TYPE_CHECKING:  # pragma: no cover - typing only
        from ..types import Step  # type: ignore

    steps: Sequence["Step"] = ()

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        maybe_module: Any = context.get("module")
        if maybe_module is None:
            return TaskResult(delta=ContextDelta(values={}))
        code = getattr(maybe_module, "code", None)
        if not isinstance(code, str):
            return TaskResult(delta=ContextDelta(values={"module": maybe_module}))
        try:
            _ = cst.parse_module(code)
        except Exception as exc:
            return TaskResult(delta=ContextDelta(values={"module": maybe_module, "postvalidator_error": str(exc)}))
        return TaskResult(delta=ContextDelta(values={"module": maybe_module}))


__all__ = ["ValidateModuleTask"]
