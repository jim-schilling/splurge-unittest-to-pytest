"""Orchestrate and run the conversion pipeline over a :class:`libcst.Module`.

Expose :func:`run_pipeline` which registers the canonical set of stages
and executes them in order over a parsed module. The function accepts an
optional ``pattern_config`` which is forwarded to stages that require
method-name matching configuration.

Publics:
    run_pipeline

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Any

import libcst as cst

from ..types import PipelineContext
from .collector import Collector
from .fixture_injector import fixture_injector_stage
from .generator import generator_stage
from .import_injector import import_injector_stage
from .manager import StageManager
from .postvalidator import postvalidator_stage
from .rewriter import rewriter_stage
from .tidy import tidy_stage

DOMAINS = ["stages", "pipeline"]

# Associated domains for this module


def run_pipeline(
    module: cst.Module,
    autocreate: bool = True,
    pattern_config: Any | None = None,
    normalize_names: bool = False,
) -> cst.Module:
    """Run the conversion pipeline on a libcst.Module and return transformed Module.

    Args:
        module: The parsed libcst.Module to transform.
        autocreate: Flag propagated to stages indicating whether autocreation
            of tmp_path-backed fixtures should be enabled.
        pattern_config: Optional PatternConfigurator injected into the
            initial pipeline context under the key 'pattern_config'. Stages
            that perform method-name matching (setup/teardown/test) should
            consult this object when present.

    Returns:
        The transformed :class:`libcst.Module`.

        If the pipeline fails or returns a non-module result, the original
        module is returned as a safe fallback.
    """
    mgr = StageManager()

    def collect_stage(context: PipelineContext) -> PipelineContext:
        # Pass through normalize_names flag so Collector can honor CLI preference
        visitor = Collector(normalize_names=bool(context.get("normalize_names", False)))
        module = context["module"]
        module.visit(visitor)
        # If diagnostics are enabled the manager can write an initial snapshot
        try:
            mgr.dump_initial(module)
        except Exception:
            pass
        return {"collector_output": visitor.as_output()}

    # The collect stage is registered after early normalization so that
    # synthetic ClassDef nodes produced by normalize_functiontestcase_stage
    # are visible to the Collector.

    # The StageManager accepts PipelineContext-typed callables; register stages directly.

    # Normalize module-level FunctionTestCase(...) call-sites into synthetic
    # TestCase-like ClassDef nodes so downstream stages can operate on a
    # single canonical representation. Run this BEFORE removing unittest
    # artifacts so alias imports like `from unittest import FunctionTestCase as FTC`
    # are still visible to the normalizer.
    from .normalize_functiontestcase import normalize_functiontestcase_stage

    mgr.register(normalize_functiontestcase_stage)

    # remove leftover unittest imports and TestCase inheritance early in the pipeline
    from .remove_unittest_artifacts import remove_unittest_artifacts_stage

    mgr.register(remove_unittest_artifacts_stage)

    # Register the typed collect stage directly now that the manager
    # accepts PipelineContext callables.
    mgr.register(collect_stage)

    # The staged pipeline is authoritative; legacy transformer paths were removed.

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

    # Register typed stages directly
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
    # Provide flags via initial context so stages can opt-in/out deterministically
    # Include an optional `pattern_config` so stages that care about method
    # name matching can consult the configured patterns.
    initial_ctx: PipelineContext = {"autocreate": autocreate}
    if pattern_config is not None:
        initial_ctx["pattern_config"] = pattern_config
    # propagate normalize_names flag into pipeline context so stages can consult
    initial_ctx["normalize_names"] = bool(normalize_names)
    # (No additional initial flags expected.)

    # StageManager.run expects a PipelineContext; pass initial_ctx directly
    context = mgr.run(module, initial_context=initial_ctx)
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
