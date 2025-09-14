"""Pipeline runner wiring the individual stages into a conversion pipeline."""

from __future__ import annotations

from typing import Any

import libcst as cst
from .collector import Collector

from .generator import generator as generator_stage
from .fixture_injector import fixture_injector_stage
from .rewriter import rewriter_stage
from .import_injector import import_injector_stage
from .manager import StageManager
from .postvalidator import postvalidator_stage
from .tidy import tidy_stage


def run_pipeline(module: cst.Module, autocreate: bool = True) -> cst.Module:
    mgr = StageManager()

    def collect_stage(context: dict[str, Any]) -> dict[str, Any]:
        visitor = Collector()
        module = context["module"]
        module.visit(visitor)
        # If diagnostics are enabled the manager can write an initial snapshot
        try:
            mgr.dump_initial(module)
        except Exception:
            pass
        return {"collector_output": visitor.as_output()}

    mgr.register(collect_stage)

    # remove leftover unittest imports and TestCase inheritance early in the pipeline
    from .remove_unittest_artifacts import remove_unittest_artifacts_stage

    mgr.register(remove_unittest_artifacts_stage)

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
    # Run decorator and mock fixes before import injection so the injector can
    # add imports required by pytest markers and other rewritten constructs.
    from .decorator_and_mock_fixes import decorator_and_mock_fixes_stage

    mgr.register(decorator_and_mock_fixes_stage)
    # Import injector should run after fixtures have been inserted so it can
    # detect the need for pytest import and place it before the @pytest.fixture
    # decorators deterministically.
    mgr.register(import_injector_stage)
    # Run post-validation before final normalization so postvalidator can
    # perform checks that might restructure the module. Apply the
    # exceptioninfo normalizer immediately before the tidy stage so the
    # AST-based ExceptionAttrRewriter runs after any stage that could
    # re-introduce `.exception` attribute accesses tied to pytest.raises
    # context managers.
    mgr.register(postvalidator_stage)
    from .raises_stage import exceptioninfo_normalizer_stage

    mgr.register(exceptioninfo_normalizer_stage)
    mgr.register(tidy_stage)

    # execute the pipeline and return the final module
    # Provide flags via initial context so stages can opt-in/out deterministically
    context = mgr.run(module, initial_context={"autocreate": autocreate})
    result = context.get("module")
    try:
        # Only call dump_final when we actually have a Module instance.
        # The manager itself also checks types at runtime, but mypy
        # requires a statically-typed call site.
        if isinstance(result, cst.Module):
            mgr.dump_final(result)  # manager will no-op if diagnostics are disabled
    except Exception:
        pass
    # context.get can return Any | None; ensure we return a Module instance
    if isinstance(result, cst.Module):
        return result
    # Fallback: return original module to keep behavior safe
    return module
