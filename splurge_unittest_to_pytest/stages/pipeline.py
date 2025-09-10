"""Pipeline runner wiring the individual stages into a conversion pipeline."""
from __future__ import annotations

from typing import Dict, Any

import libcst as cst
from .collector import Collector
from .generator import generator_stage
from .fixture_injector import fixture_injector_stage
from .rewriter import rewriter_stage
from .import_injector import import_injector_stage
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

    # Note: legacy transformer previously ran early here.
    # Per project decision to ignore legacy behavior and make the staged
    # pipeline authoritative, we no longer run the legacy transformer here.
    # If backward-compat behavior is ever required, reintroduce this wrapper
    # behind an explicit flag.

    # core pipeline stages
    # assertion rewriter: convert self.assert* -> pytest assert and assertRaises contexts
    from .assertion_rewriter import assertion_rewriter_stage
    mgr.register(assertion_rewriter_stage)
    from .raises_stage import raises_stage
    mgr.register(raises_stage)

    mgr.register(generator_stage)
    mgr.register(rewriter_stage)
    # Insert fixtures stage to convert class setUp/tearDown to fixtures and
    # update test function signatures before injecting fixture FunctionDefs
    from .fixtures_stage import fixtures_stage
    mgr.register(fixtures_stage)
    mgr.register(fixture_injector_stage)
    # Import injector should run after fixtures have been inserted so it can
    # detect the need for pytest import and place it before the @pytest.fixture
    # decorators deterministically.
    mgr.register(import_injector_stage)
    mgr.register(postvalidator_stage)
    mgr.register(tidy_stage)

    # execute the pipeline and return the final module
    context = mgr.run(module)
    return context.get("module")
