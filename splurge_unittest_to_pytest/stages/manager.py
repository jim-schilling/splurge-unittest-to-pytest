"""StageManager skeleton for orchestrating converter stages.

This minimal manager supports registering callables that accept and return a
`context` mapping. The context starts with the `module` (cst.Module) and may be
extended with stage outputs (e.g., collector_output).
"""
from __future__ import annotations

from typing import Any, Callable

import libcst as cst
from pathlib import Path
from . import diagnostics

StageCallable = Callable[[dict[str, Any]], dict[str, Any]]


class StageManager:
    def __init__(self, stages: list[StageCallable] | None = None) -> None:
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
        # Wrap the stage so we can dump the module after it runs for
        # deterministic debugging output without modifying stage code.
        def wrapped_stage(context: dict[str, Any]) -> dict[str, Any]:
            result = stage(context)
            # merge result like run() would
            if isinstance(result, dict):
                context.update(result)
            # Dump current module snapshot
            try:
                current_module = context.get("module")
                # Only write intermediate debug snapshots when diagnostics are
                # explicitly enabled via environment variable. This prevents
                # the pipeline from creating 'build/intermediates' during
                # normal development or test runs.
                if self._diagnostics_dir is not None and isinstance(current_module, cst.Module):
                    stage_name = getattr(stage, "__name__", "<stage>")
                    idx = len(list(self._diagnostics_dir.iterdir()))
                    diagnostics.write_snapshot(self._diagnostics_dir, f"{idx:02d}_{stage_name}.py", current_module)
            except Exception:
                pass
            return result

        self.stages.append(wrapped_stage)

    def run(self, module: cst.Module, initial_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run registered stages over `module`.

        An optional `initial_context` dict can be provided to seed the pipeline
        context (for example configuration flags like 'autocreate'). This is
        used by the pipeline runner to pass CLI/runtime options into stages.
        """
        context: dict[str, Any] = {"module": module}
        if initial_context and isinstance(initial_context, dict):
            # Merge initial context values (do not override module)
            for k, v in initial_context.items():
                if k != "module":
                    context[k] = v
        for stage in self.stages:
            result = stage(context)
            # allow stages to either mutate context in-place or return a new
            # dict with their outputs; merge conservatively
            if result is None:
                continue
            if isinstance(result, dict):
                context.update(result)
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
