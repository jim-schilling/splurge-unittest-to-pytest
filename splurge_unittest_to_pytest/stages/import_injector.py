"""Deterministically ensure required imports exist in a module.

This stage inspects the pipeline context for flags such as
``needs_pytest_import`` or a set of ``needs_typing_names`` and
inserts minimal import statements at a deterministic location in the
module (after the docstring or existing imports). The injector avoids
duplicating existing imports and will merge or create a single
``from typing import ...`` statement when typing names are requested.

Publics:
    import_injector_stage

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Optional, cast
from ..types import PipelineContext
from .steps import run_steps
from .steps_import_injector import DetectNeedsStep, InsertImportsStep
from .events import EventBus, TaskErrored

import libcst as cst

DOMAINS = ["stages", "imports"]
STAGE_ID = "stages.import_injector"
STAGE_VERSION = "1"

# Associated domains for this module


def import_injector_stage(context: PipelineContext) -> PipelineContext:
    """Pipeline stage that ensures required imports exist in the module.

    Inspects context flags (for example ``needs_pytest_import``) and scans
    the module to detect and insert required imports deterministically.
    """

    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is None:
        return cast(PipelineContext, {})

    # Stage-2 pilot: run two Steps to determine needs and insert imports.
    stage_id = "stages.import_injector"
    # ensure stage id is visible to steps
    working = cast(PipelineContext, dict(context))
    working["__stage_id__"] = stage_id
    bus = working.get("__event_bus__")

    # Execute DetectNeedsStep then InsertImportsStep via run_steps which folds
    # deltas and preserves the event/hook lifecycle for steps.
    try:
        # Run DetectNeedsStep first to determine which imports are required.
        detect_task_id = "tasks.import_injector.detect_needs"
        detect_task_name = "detect_needs"
        detect_result = run_steps(
            stage_id, detect_task_id, detect_task_name, [DetectNeedsStep()], working, resources=None
        )
        if detect_result.errors:
            if isinstance(bus, EventBus):
                try:
                    bus.publish(
                        TaskErrored(run_id="", stage_id=stage_id, task_id=detect_task_id, error=detect_result.errors[0])
                    )
                except Exception:
                    pass
            return cast(PipelineContext, {"module": module})

        # Merge detect deltas into working context for the insert step.
        #
        # mypy notes: `PipelineContext` is a TypedDict which enforces key
        # constraints at type-check time. `detect_result.delta.values` is a
        # plain dict[str, Any] at runtime; passing that directly to
        # `TypedDict.update()` triggers a mypy complaint about the argument
        # type. We coerce to `PipelineContext` with `cast()` here to satisfy
        # static checking while preserving the exact runtime behavior (the
        # value is still a plain dict and update() operates normally). This
        # is a harmless, intentional type-only coercion to keep the code
        # both type-safe and practical.
        working.update(cast(PipelineContext, dict(detect_result.delta.values)))

        # Run InsertImportsStep to ensure required imports exist
        insert_task_id = "tasks.import_injector.insert_imports"
        insert_task_name = "insert_imports"
        insert_result = run_steps(
            stage_id, insert_task_id, insert_task_name, [InsertImportsStep()], working, resources=None
        )
        if insert_result.errors:
            if isinstance(bus, EventBus):
                try:
                    bus.publish(
                        TaskErrored(run_id="", stage_id=stage_id, task_id=insert_task_id, error=insert_result.errors[0])
                    )
                except Exception:
                    pass
            return cast(PipelineContext, {"module": module})

        # Merge and return final deltas
        final_vals = dict(detect_result.delta.values)
        final_vals.update(insert_result.delta.values)
        return cast(PipelineContext, final_vals)
    except Exception:
        return cast(PipelineContext, {"module": module})
