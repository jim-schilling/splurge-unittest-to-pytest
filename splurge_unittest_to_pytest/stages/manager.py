"""Stage manager: register, wrap, and execute pipeline stages.

This module provides :class:`StageManager` which registers stage callables
and executes them sequentially over a shared context mapping. The
manager wraps stages to optionally write intermediate diagnostics
snapshots when diagnostics are enabled; it also exposes helpers to dump
initial and final module snapshots.

Publics:
    StageManager

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Callable, Any, cast
import uuid

import libcst as cst
from pathlib import Path
from . import diagnostics

from ..types import PipelineContext
from .events import (
    EventBus,
    PipelineStarted,
    PipelineCompleted,
    StageStarted,
    StageCompleted,
    DiagnosticsObserver,
    LoggingObserver,
    logging_enabled,
    HookRegistry,
)
from .events import StageLogger, logging_enabled_stages

DOMAINS = ["stages", "manager"]

# Stage callables accept and return PipelineContext directly.
StageCallable = Callable[[PipelineContext], PipelineContext]

# Associated domains for this module


class StageManager:
    def __init__(
        self,
        stages: list[StageCallable] | None = None,
    ) -> None:
        self.stages: list[StageCallable] = stages or []
        # If diagnostics are enabled, create a temporary directory for this
        # run and place a timestamped marker file in the system temp dir so
        # callers can discover diagnostics artifacts. The marker file is an
        # empty file named splurge-diagnostics-YYYY-MM-DD_HH-MM-SS in the
        # system temporary directory.
        # Diagnostics directory (created when diagnostics are enabled)
        self._diagnostics_dir: Path | None = diagnostics.create_diagnostics_dir()
        # Stage-0 scaffolding: resources/event bus
        self._event_bus: EventBus = EventBus()
        self._run_id: str = uuid.uuid4().hex
        self._hooks = HookRegistry()
        self._stage_versions: dict[str, str] = {}
        # Stage-1: install default observers (diagnostics + logging)
        try:
            # Diagnostics observer is controlled by diagnostics env vars
            self._event_bus.subscribe(StageCompleted, DiagnosticsObserver(self._diagnostics_dir))
            # Logging observers gated by SPLURGE_ENABLE_PIPELINE_LOGS
            if logging_enabled():
                log_obs = LoggingObserver()
                self._event_bus.subscribe(PipelineStarted, log_obs)
                self._event_bus.subscribe(PipelineCompleted, log_obs)
                self._event_bus.subscribe(StageStarted, log_obs)
                self._event_bus.subscribe(StageCompleted, log_obs)
            # Per-stage debug logger (optional, controlled by env var or run-time flag)
            if logging_enabled_stages():
                stage_logger = StageLogger()
                self._event_bus.subscribe(StageStarted, stage_logger)
                self._event_bus.subscribe(StageCompleted, stage_logger)
        except Exception:
            pass

    def _diagnostics_enabled(self) -> bool:
        """Return True when diagnostics are enabled via environment.

        Delegates to the `diagnostics` helper to centralize truthiness checks.
        """
        return diagnostics.diagnostics_enabled()

    def dump_initial(self, module: cst.Module) -> None:
        """Write an initial snapshot of the module to the diagnostics dir.

        This is a public helper so callers (for example the pipeline runner)
        can request a named initial snapshot without embedding write logic.
        """
        try:
            diagnostics.write_snapshot(self._diagnostics_dir, "00_initial_input.py", module)
        except Exception:
            pass

    def dump_final(self, module: cst.Module) -> None:
        """Write the final module snapshot to the diagnostics dir."""
        try:
            diagnostics.write_snapshot(self._diagnostics_dir, "99_final_output.py", module)
        except Exception:
            pass

    def register(self, stage: StageCallable) -> None:
        """Register a typed stage.

        Stages are kept as typed callables and executed by :meth:`run`, which
        is responsible for merging outputs and writing diagnostics snapshots.
        """
        self.stages.append(stage)

    def run(
        self,
        module: cst.Module,
        initial_context: PipelineContext | None = None,
    ) -> PipelineContext:
        """Run registered stages over `module`.

        Args:
            module: The :class:`libcst.Module` to operate on.
            initial_context: Optional mapping to seed the pipeline context (for
                example configuration flags like ``'autocreate'``). This is used
                by the pipeline runner to pass CLI/runtime options into stages.

        Returns:
            The final pipeline context mapping after all stages have executed.
        """
        context: PipelineContext = {"module": module}
        # Emit pipeline started (Stage-0: no behavior change)
        try:
            self._event_bus.publish(PipelineStarted(self._run_id))
        except Exception:
            pass
        # Use an untyped view when merging arbitrary keys to avoid mypy
        # TypedDict key restrictions; PipelineContext remains the runtime
        # representation.
        untyped_ctx = cast(dict[str, Any], context)
        if initial_context:
            # Merge initial context values (do not override module)
            for k, v in initial_context.items():
                if k != "module":
                    untyped_ctx[k] = v
        # Expose bus and hooks to stages (opt-in usage by pilot Task-based stages)
        untyped_ctx["__event_bus__"] = self._event_bus
        untyped_ctx["__hooks__"] = self._hooks
        for idx, stage in enumerate(self.stages, start=1):
            # Each stage accepts and returns a PipelineContext mapping.
            try:
                # Publish stage start event
                stage_name = getattr(stage, "__name__", "<stage>")
                stage_id = f"stages.{stage_name}"
                # If the stage module provides STAGE_VERSION, use it
                try:
                    mod = getattr(stage, "__module__", None)
                    if isinstance(mod, str):
                        import importlib

                        m = importlib.import_module(mod)
                        version = getattr(m, "STAGE_VERSION", self._stage_versions.get(stage_name, "1"))
                        self._stage_versions[stage_name] = str(version)
                    else:
                        version = self._stage_versions.get(stage_name, "1")
                except Exception:
                    version = self._stage_versions.get(stage_name, "1")
                self._event_bus.publish(StageStarted(self._run_id, stage_id, stage_name, version, idx))
            except Exception:
                pass
            # Trigger before_stage hook (best-effort)
            try:
                self._hooks.before_stage(getattr(stage, "__name__", "<stage>"), untyped_ctx)
            except Exception:
                pass
            result = stage(context)
            # allow stages to either mutate context in-place or return a new
            # mapping; merge conservatively
            if result is None:
                continue
            if isinstance(result, dict):
                untyped_ctx.update(result)
            # Publish stage completed event with module for observers
            try:
                current_module = context.get("module")
                stage_name = getattr(stage, "__name__", "<stage>")
                stage_id = f"stages.{stage_name}"
                version = self._stage_versions.get(stage_name, "1")
                self._event_bus.publish(
                    StageCompleted(self._run_id, stage_id, stage_name, version, idx, current_module)
                )
            except Exception:
                pass
            # Trigger after_stage hook with result
            try:
                self._hooks.after_stage(getattr(stage, "__name__", "<stage>"), cast(dict[str, Any], result))
            except Exception:
                pass
        # Emit pipeline completed
        try:
            self._event_bus.publish(PipelineCompleted(self._run_id))
        except Exception:
            pass
        return context
