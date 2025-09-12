"""StageManager skeleton for orchestrating converter stages.

This minimal manager supports registering callables that accept and return a
`context` mapping. The context starts with the `module` (cst.Module) and may be
extended with stage outputs (e.g., collector_output).
"""
from __future__ import annotations

from typing import Any, Callable

import libcst as cst
from pathlib import Path
import os
import tempfile
from datetime import datetime

StageCallable = Callable[[dict[str, Any]], dict[str, Any]]


class StageManager:
    def __init__(self, stages: list[StageCallable] | None = None) -> None:
        self.stages: list[StageCallable] = stages or []
        # If diagnostics are enabled, create a temporary directory for this
        # run and place a timestamped marker file in the system temp dir so
        # callers can discover diagnostics artifacts. The marker file is an
        # empty file named splurge-diagnostics-YYYY-MM-DD_HH-MM-SS in the
        # system temporary directory.
        self._diagnostics_dir: Path | None = None
        if self._diagnostics_enabled():
            # Create a temp directory specific to this run
            tmpdir = tempfile.mkdtemp(prefix="splurge-diagnostics-")
            self._diagnostics_dir = Path(tmpdir)
            # Create the marker file inside the diagnostics temp directory
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            marker = self._diagnostics_dir / f"splurge-diagnostics-{ts}"
            try:
                # Write the absolute diagnostics folder path into the marker
                # file so callers can easily discover where artifacts live.
                marker.write_text(str(self._diagnostics_dir.resolve()), encoding="utf-8")
            except Exception:
                # Swallow errors creating the marker; diagnostics are opt-in
                self._diagnostics_dir = None

    def _diagnostics_enabled(self) -> bool:
        """Return True when the SPLURGE_ENABLE_DIAGNOSTICS env var is set to a
        truthy value. Accept common truthy strings for convenience.
        """
        val = os.environ.get("SPLURGE_ENABLE_DIAGNOSTICS", "0")
        return val in ("1", "true", "True", "yes", "on")

    def dump_initial(self, module: cst.Module) -> None:
        """Write an initial snapshot of the module to the diagnostics dir.

        This is a public helper so callers (for example the pipeline runner)
        can request a named initial snapshot without embedding write logic.
        """
        try:
            if self._diagnostics_dir is None:
                return
            if not isinstance(module, cst.Module):
                return
            out_dir = self._diagnostics_dir
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "00_initial_input.py"
            src = getattr(module, "code", None)
            if src is None:
                try:
                    src = module.code
                except Exception:
                    src = None
            if src is not None:
                out_path.write_text(src, encoding="utf-8")
        except Exception:
            pass

    def dump_final(self, module: cst.Module) -> None:
        """Write the final module snapshot to the diagnostics dir."""
        try:
            if self._diagnostics_dir is None:
                return
            if not isinstance(module, cst.Module):
                return
            out_dir = self._diagnostics_dir
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "99_final_output.py"
            src = getattr(module, "code", None)
            if src is None:
                try:
                    src = module.code
                except Exception:
                    src = None
            if src is not None:
                out_path.write_text(src, encoding="utf-8")
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
                if self._diagnostics_dir is not None:
                    if isinstance(current_module, cst.Module):
                        out_dir = self._diagnostics_dir
                        out_dir.mkdir(parents=True, exist_ok=True)
                        stage_name = getattr(stage, "__name__", "<stage>")
                        idx = len(list(out_dir.iterdir()))
                        out_path = out_dir / f"{idx:02d}_{stage_name}.py"
                        src = getattr(current_module, "code", None)
                        if src is None:
                            try:
                                src = current_module.code
                            except Exception:
                                src = None
                        if src is not None:
                            out_path.write_text(src, encoding="utf-8")
            except Exception:
                pass
            return result

        self.stages.append(wrapped_stage)

    def run(self, module: cst.Module) -> dict[str, Any]:
        context: dict[str, Any] = {"module": module}
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
                # explicitly enabled.
                if self._diagnostics_dir is not None:
                    current_module = context.get("module")
                    if isinstance(current_module, cst.Module):
                        out_dir = self._diagnostics_dir
                        out_dir.mkdir(parents=True, exist_ok=True)
                        stage_name = getattr(stage, "__name__", f"stage_{len(list(out_dir.iterdir()))}")
                        idx = len(list(out_dir.iterdir()))
                        out_path = out_dir / f"{idx:02d}_{stage_name}.py"
                        # libcst.Module provides .code attribute
                        src = getattr(current_module, "code", None)
                        if src is None:
                            try:
                                src = current_module.code
                            except Exception:
                                src = None
                        if src is not None:
                            out_path.write_text(src, encoding="utf-8")
            except Exception:
                # Do not let debugging instrumentation break the pipeline
                pass
        return context
