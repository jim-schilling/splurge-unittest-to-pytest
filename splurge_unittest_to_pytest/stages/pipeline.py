"""Pipeline runner wiring the individual stages into a conversion pipeline."""
from __future__ import annotations

from typing import Dict, Any

import libcst as cst
from .collector import Collector
from .generator import generator_stage
from .import_injector import import_injector_stage
from .fixture_injector import fixture_injector_stage
from .manager import StageManager
from .postvalidator import postvalidator_stage
from .tidy import tidy_stage


def run_pipeline(module: cst.Module, compat: bool = True) -> cst.Module:
    mgr = StageManager()

    def collect_stage(context: Dict[str, Any]) -> Dict[str, Any]:
        visitor = Collector()
        module = context["module"]
        module.visit(visitor)
        return {"collector_output": visitor.as_output()}

    mgr.register(collect_stage)
    mgr.register(generator_stage)
    mgr.register(import_injector_stage)

    def fixture_stage_wrapper(ctx: Dict[str, Any]) -> Dict[str, Any]:
        # ensure compat gets forwarded
        ctx = dict(ctx)
        ctx.setdefault("compat", compat)
        return fixture_injector_stage(ctx)

    mgr.register(fixture_stage_wrapper)
    # run post-validation and tidy
    mgr.register(postvalidator_stage)
    mgr.register(tidy_stage)
    ctx = mgr.run(module)
    return ctx.get("module")
