"""Pipeline runner wiring the individual stages into a conversion pipeline."""
from __future__ import annotations

from typing import Dict, Any

import libcst as cst
from .collector import Collector
from .generator import generator_stage
from .import_injector import import_injector_stage
from .fixture_injector import fixture_injector_stage
from .rewriter import rewriter_stage
from ..converter import UnittestToPytestTransformer
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

    # Run the legacy transformer early so assertion/class conversions happen before generator
    def legacy_transform_wrapper(ctx: Dict[str, Any]) -> Dict[str, Any]:
        ctx = dict(ctx)
        ctx.setdefault("compat", compat)
        module = ctx.get("module")
        if module is None:
            return {"module": module}
        transformer = UnittestToPytestTransformer(compat=compat)
        new_module = module.visit(transformer)
        return {"module": new_module}

    mgr.register(legacy_transform_wrapper)

    # core pipeline stages
    # assertion rewriter: convert self.assert* -> pytest assert and assertRaises contexts
    from .assertion_rewriter import assertion_rewriter_stage
    mgr.register(assertion_rewriter_stage)

    mgr.register(generator_stage)
    mgr.register(import_injector_stage)
    mgr.register(rewriter_stage)
    mgr.register(fixture_injector_stage)
    mgr.register(postvalidator_stage)
    mgr.register(tidy_stage)

    # execute the pipeline and return the final module
    context = mgr.run(module)
    return context.get("module")
