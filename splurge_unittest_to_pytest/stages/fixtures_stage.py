"""Transform TestCase setup/teardown into pytest fixtures and functions.

Consume :class:`CollectorOutput` and emit top-level pytest functions
and/or fixtures derived from recorded setup assignments. A
``pattern_config`` object may be supplied in the pipeline context to
customize method-name matching for setup/teardown detection.

Publics:
    fixtures_stage

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, cast
from ..types import PipelineContext
from .fixtures_stage_tasks import BuildTopLevelTestsTask
from .events import EventBus, TaskStarted, TaskCompleted, TaskErrored

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput
from splurge_unittest_to_pytest.converter.method_params import (
    is_classmethod,
    is_staticmethod,
    first_param_name,
)

DOMAINS = ["stages", "fixtures"]
STAGE_ID = "stages.fixtures_stage"
STAGE_VERSION = "1"


# Associated domains for this module


# NOTE: helper to decide removal of first param was removed; the current
# staged pipeline keeps instance/class first params to make converted modules
# runnable by default and uses an autouse attach fixture for pytest runs.


def _update_test_function(
    fn: cst.FunctionDef,
    fixture_names: Sequence[str],
    remove_first: bool,
) -> cst.FunctionDef:
    """Update a test method's parameters for pytest conversion.

    Args:
        fn: The original :class:`libcst.FunctionDef` representing the method.
        fixture_names: Sequence of fixture parameter names to append when the
            first parameter is removed.
        remove_first: When ``True`` drop the original first parameter
            (``self``/``cls``) and append the fixture parameters. When
            ``False`` retain the first parameter for runnability.

    Returns:
        A new :class:`libcst.FunctionDef` with updated parameters.
    """
    params = list(fn.params.params)
    # detect staticmethod/classmethod decorators using consolidated helpers
    if not is_staticmethod(fn):
        if remove_first:
            # drop first param if it's self/cls
            if params:
                fname = first_param_name(fn)
                if fname in ("self", "cls"):
                    params = params[1:]
        else:
            desired_first = cst.Name("cls") if is_classmethod(fn) else cst.Name("self")
            f_name = first_param_name(fn)
            if f_name not in ("self", "cls"):
                # insert desired first param
                params.insert(0, cst.Param(name=desired_first))

    # Append fixture parameters only when we've removed the first param
    # (i.e., converting TestCase methods into plain pytest functions). If
    # we keep the method runnable (retain self/cls), do not append fixture
    # params and rely on the autouse attach fixture to set instance attrs.
    if remove_first:
        for fname in fixture_names:
            params.append(cst.Param(name=cst.Name(fname)))

    new_params = fn.params.with_changes(params=params)
    return fn.with_changes(params=new_params)


def fixtures_stage(context: PipelineContext) -> PipelineContext:
    module: Optional[cst.Module] = context.get("module")
    collector: Optional[CollectorOutput] = context.get("collector_output")
    # fixture_specs may be provided by earlier stages; they are not needed
    # in this stage's current implementation but may be present in the
    # context. We intentionally do not use them here to keep this stage
    # focused on producing runnable classes and top-level wrappers.

    if module is None or collector is None:
        return cast(PipelineContext, {"module": module})

    # Allow configurable setup/teardown name lists via a PatternConfigurator
    # provided in the pipeline context under the 'pattern_config' key.
    pattern_config: Optional[Any] = context.get("pattern_config")

    def _is_setup_name(name: str) -> bool:
        # If a PatternConfigurator is provided, use its normalized matching
        # helpers; otherwise fall back to common defaults.
        try:
            if pattern_config is not None:
                return bool(getattr(pattern_config, "_is_setup_method", lambda n: False)(name))
        except Exception:
            pass
        return name in ("setUp", "setUpClass")

    def _is_teardown_name(name: str) -> bool:
        try:
            if pattern_config is not None:
                return bool(getattr(pattern_config, "_is_teardown_method", lambda n: False)(name))
        except Exception:
            pass
        return name in ("tearDown", "tearDownClass")

    stage_id = "stages.fixtures_stage"
    bus = context.get("__event_bus__")
    # Stage-4: delegate to BuildTopLevelTestsTask and emit per-task events
    task = BuildTopLevelTestsTask()
    # If a PatternConfigurator requests certain setup method names be
    # treated as patterns to remove, strip those methods from ClassDef
    # nodes so the BuildTopLevelTestsTask does not re-emit them.
    try:
        if pattern_config is not None:
            # pattern_config exposes '_is_setup_method' to test membership
            def _strip_pattern_methods(mod: cst.Module) -> cst.Module:
                class _Stripper(cst.CSTTransformer):
                    def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef) -> cst.ClassDef:
                        try:
                            new_body = [
                                m
                                for m in original.body.body
                                if not (
                                    isinstance(m, cst.FunctionDef)
                                    and getattr(pattern_config, "_is_setup_method")(m.name.value)
                                )
                            ]
                            # new_body may contain BaseSmallStatement values;
                            # cast to Sequence[BaseStatement] for IndentedBlock
                            return updated.with_changes(
                                body=cst.IndentedBlock(body=list(cast(Sequence[cst.BaseStatement], new_body)))
                            )
                        except Exception:
                            return updated

                return mod.visit(_Stripper())

            try:
                module = _strip_pattern_methods(module)
            except Exception:
                pass
    except Exception:
        pass
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=task.id))
        res = task.execute(context, resources=None)
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=task.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=task.id, error=exc))
        return cast(PipelineContext, {"module": module})
    return cast(PipelineContext, res.delta.values)
