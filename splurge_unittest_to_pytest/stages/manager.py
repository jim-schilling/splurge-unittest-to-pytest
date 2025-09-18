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

import libcst as cst
from pathlib import Path
from . import diagnostics

from ..types import PipelineContext

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
        # Use an untyped view when merging arbitrary keys to avoid mypy
        # TypedDict key restrictions; PipelineContext remains the runtime
        # representation.
        untyped_ctx = cast(dict[str, Any], context)
        if initial_context:
            # Merge initial context values (do not override module)
            for k, v in initial_context.items():
                if k != "module":
                    untyped_ctx[k] = v
        for stage in self.stages:
            # Each stage accepts and returns a PipelineContext mapping.
            result = stage(context)
            # allow stages to either mutate context in-place or return a new
            # mapping; merge conservatively
            if result is None:
                continue
            if isinstance(result, dict):
                untyped_ctx.update(result)
            # Debug: dump the current module source after this stage for
            # inspection during pipeline debugging. Files are written under
            # build/intermediates/<index>_<stage_name>.py
            try:
                # Only write intermediate debug snapshots when diagnostics are
                # explicitly enabled. Delegate to diagnostics.write_snapshot
                # which is defensive and will no-op on None/invalid inputs.
                current_module = context.get("module")
                if self._diagnostics_dir is not None and isinstance(current_module, cst.Module):
                    stage_name = getattr(stage, "__name__", "<stage>")
                    idx = len(list(self._diagnostics_dir.iterdir()))
                    diagnostics.write_snapshot(self._diagnostics_dir, f"{idx:02d}_{stage_name}.py", current_module)
            except Exception:
                # Do not let debugging instrumentation break the pipeline
                pass
        return context
