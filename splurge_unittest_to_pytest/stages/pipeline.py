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

from typing import Any, cast, Callable

import libcst as cst
from .collector import Collector
from ..types import PipelineContext

from .generator import generator as generator_stage
from .fixture_injector import fixture_injector_stage
from .rewriter import rewriter_stage
from .import_injector import import_injector_stage
from .manager import StageManager
from .postvalidator import postvalidator_stage
from .tidy import tidy_stage

DOMAINS = ["stages", "pipeline"]

# Associated domains for this module


def run_pipeline(module: cst.Module, autocreate: bool = True, pattern_config: Any | None = None) -> cst.Module:
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

    def collect_stage(context: dict[str, Any]) -> dict[str, Any]:
        # Cast to the typed PipelineContext for internal use
        pctx = cast(PipelineContext, context)
        visitor = Collector()
        module = pctx["module"]
        module.visit(visitor)
        # If diagnostics are enabled the manager can write an initial snapshot
        try:
            mgr.dump_initial(module)
        except Exception:
            pass
        return {"collector_output": visitor.as_output()}

    # StageManager.register expects callables of signature
    # Callable[[dict[str, Any]], dict[str, Any]]. Provide a thin adapter
    # that accepts the untyped mapping and forwards it to the typed
    # implementation so mypy and runtime agree about the interface.
    def _collect_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
        return collect_stage(ctx)  # type: ignore[return-value]

    mgr.register(_collect_adapter)

    # Generic wrapper to adapt any stage (typed or untyped) into the
    # manager-expected Callable[[dict[str, Any]], dict[str, Any]]. We
    # cast inputs/outputs conservatively inside the adapter so stages can
    # be gradually migrated to PipelineContext without changing the
    # manager's public API.
    def _wrap_any(stage: Callable[..., Any]) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def _adapter(ctx: dict[str, Any]) -> dict[str, Any]:
            # TODO(jim): remove this adapter once all stages and StageManager
            # accept and expose PipelineContext (TypedDict) directly. Keep
            # this thin adapter as a temporary bridge during the incremental
            # migration; it should be deleted when the codebase no longer
            # requires casts around registration.
            res = stage(cast(PipelineContext, ctx))
            return cast(dict[str, Any], res)

        return _adapter

    # remove leftover unittest imports and TestCase inheritance early in the pipeline
    from .remove_unittest_artifacts import remove_unittest_artifacts_stage

    # Wrap other stages with thin adapters when necessary so the StageManager
    # always receives callables matching Callable[[dict[str, Any]], dict[str, Any]].
    mgr.register(_wrap_any(remove_unittest_artifacts_stage))

    # Note: legacy transformer previously ran early here.
    # Per project decision to ignore legacy behavior and make the staged
    # pipeline authoritative, we no longer run the legacy transformer here.
    # If backward-compat behavior is ever required, reintroduce this wrapper
    # behind an explicit flag.

    # core pipeline stages
    # assertion rewriter: convert self.assert* -> pytest assert and assertRaises contexts
    from .assertion_rewriter import assertion_rewriter_stage

    mgr.register(_wrap_any(assertion_rewriter_stage))
    from .raises_stage import raises_stage

    mgr.register(_wrap_any(raises_stage))

    mgr.register(_wrap_any(generator_stage))
    mgr.register(_wrap_any(rewriter_stage))
    # Insert fixtures stage to convert class setUp/tearDown to fixtures and
    # update test function signatures before injecting fixture FunctionDefs
    from .fixtures_stage import fixtures_stage

    # Provide a thin helper to wrap typed PipelineContext stages so the
    # StageManager continues to receive callables that accept an untyped
    # dict[str, Any] and return dict[str, Any]. This keeps StageManager's
    # public signature unchanged and confines typed usage inside stages.
    def _wrap(typed_stage: Callable[[PipelineContext], PipelineContext]) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def _adapter(ctx: dict[str, Any]) -> dict[str, Any]:
            res = typed_stage(cast(PipelineContext, ctx))
            return cast(dict[str, Any], res)

        return _adapter

    # Register stages through the adapter to preserve the manager's untyped API
    mgr.register(_wrap(fixtures_stage))
    mgr.register(_wrap(fixture_injector_stage))
    # Run decorator and mock fixes before import injection so the injector can
    # add imports required by pytest markers and other rewritten constructs.
    from .decorator_and_mock_fixes import decorator_and_mock_fixes_stage

    mgr.register(_wrap_any(decorator_and_mock_fixes_stage))
    # Import injector should run after fixtures have been inserted so it can
    # detect the need for pytest import and place it before the @pytest.fixture
    # decorators deterministically.
    mgr.register(_wrap_any(import_injector_stage))
    # Run post-validation before final normalization so postvalidator can
    # perform checks that might restructure the module. Apply the
    # exceptioninfo normalizer immediately before the tidy stage so the
    # AST-based ExceptionAttrRewriter runs after any stage that could
    # re-introduce `.exception` attribute accesses tied to pytest.raises
    # context managers.
    mgr.register(_wrap_any(postvalidator_stage))
    from .raises_stage import exceptioninfo_normalizer_stage

    mgr.register(_wrap_any(exceptioninfo_normalizer_stage))
    mgr.register(_wrap_any(tidy_stage))

    # execute the pipeline and return the final module
    # Provide flags via initial context so stages can opt-in/out deterministically
    # Provide flags via initial context so stages can opt-in/out deterministically
    # Include an optional `pattern_config` so stages that care about method
    # name matching can consult the configured patterns.
    initial_ctx: PipelineContext = {"autocreate": autocreate}
    if pattern_config is not None:
        initial_ctx["pattern_config"] = pattern_config

    # StageManager.run expects a dict[str, Any]; cast initial_ctx accordingly
    context = cast(PipelineContext, mgr.run(module, initial_context=cast(dict[str, Any], initial_ctx)))
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
