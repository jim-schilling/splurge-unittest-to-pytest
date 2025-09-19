"""Minimal internal event bus and typed events for the staged pipeline.

Publics:
    EventBus
    RecordingObserver
    PipelineStarted, PipelineCompleted
    StageStarted, StageCompleted, StageErrored
    TaskStarted, TaskCompleted, TaskSkipped, TaskErrored

Design notes:
- This is intentionally small and dependency-free. Observers subscribe to
  event types by name; errors in observers are isolated and do not affect
  pipeline execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, DefaultDict
from collections import defaultdict
from pathlib import Path
import os
from . import diagnostics


DOMAINS = ["stages", "events", "pipeline"]


# Event definitions (lightweight dataclasses)
@dataclass(frozen=True)
class PipelineStarted:
    run_id: str


@dataclass(frozen=True)
class PipelineCompleted:
    run_id: str


@dataclass(frozen=True)
class StageStarted:
    run_id: str
    stage_id: str
    stage_name: str
    version: str
    index: int


@dataclass(frozen=True)
class StageCompleted:
    run_id: str
    stage_id: str
    stage_name: str
    version: str
    index: int
    module: Any


@dataclass(frozen=True)
class StageErrored:
    run_id: str
    stage_id: str
    error: Exception


@dataclass(frozen=True)
class TaskStarted:
    run_id: str
    stage_id: str
    task_id: str


@dataclass(frozen=True)
class TaskCompleted:
    run_id: str
    stage_id: str
    task_id: str


@dataclass(frozen=True)
class TaskSkipped:
    run_id: str
    stage_id: str
    task_id: str


@dataclass(frozen=True)
class TaskErrored:
    run_id: str
    stage_id: str
    task_id: str
    error: Exception


Event = Any
Observer = Callable[[Event], None]


class EventBus:
    """Simple pub/sub bus keyed by event class name."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, list[Observer]] = defaultdict(list)

    def subscribe(self, event_type: type, observer: Observer) -> None:
        self._subscribers[event_type.__name__].append(observer)

    def publish(self, event: Event) -> None:
        name = type(event).__name__
        for observer in list(self._subscribers.get(name, [])):
            try:
                observer(event)
            except Exception:
                # isolate observer errors
                pass


class RecordingObserver:
    """Test helper that records events in order."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        self.events.append(event)


class DiagnosticsObserver:
    """Observer that writes stage-completed snapshots deterministically.

    Relies on existing diagnostics env flags to decide whether to write.
    """

    def __init__(self, out_dir: Path | None) -> None:
        self._out_dir = out_dir

    def __call__(self, event: Event) -> None:
        try:
            if not diagnostics.diagnostics_enabled():
                return
            if type(event).__name__ != "StageCompleted":
                return
            # mypy: duck-type the event
            name = getattr(event, "stage_name", "stage")
            index = getattr(event, "index", 0)
            module = getattr(event, "module", None)
            diagnostics.write_snapshot(self._out_dir, f"{index:02d}_{name}.py", module)
        except Exception:
            # never break the pipeline
            pass


class LoggingObserver:
    """Observer that logs pipeline lifecycle events via stdlib logging."""

    def __init__(self) -> None:
        import logging

        self._log = logging.getLogger("splurge.pipeline")

    def __call__(self, event: Event) -> None:
        try:
            name = type(event).__name__
            payload = getattr(event, "__dict__", {})
            self._log.debug("pipeline_event %s %s", name, payload)
        except Exception:
            pass


class StageLogger:
    """Observer that emits lightweight pre/post stage debug messages.

    Records per-stage start times and logs a debug message on completion
    including the duration and a small context summary. This observer is
    intentionally conservative: it logs only names, indices, duration (ms),
    and a brief context key-count to avoid dumping large ASTs or secrets.
    """

    def __init__(self) -> None:
        import logging

        self._log = logging.getLogger("splurge.pipeline.stage")
        self._times: dict[tuple[str, str], float] = {}

    def __call__(self, event: Event) -> None:
        try:
            import time

            name = type(event).__name__
            if name == "StageStarted":
                run_id = getattr(event, "run_id", "")
                stage_id = getattr(event, "stage_id", "")
                self._times[(run_id, stage_id)] = time.perf_counter()
                self._log.debug(
                    "stage.pre %s idx=%s id=%s",
                    getattr(event, "stage_name", "<stage>"),
                    getattr(event, "index", 0),
                    stage_id,
                )
            elif name == "StageCompleted":
                run_id = getattr(event, "run_id", "")
                stage_id = getattr(event, "stage_id", "")
                start = self._times.pop((run_id, stage_id), None)
                duration_ms = None
                if start is not None:
                    duration_ms = int((time.perf_counter() - start) * 1000)
                # small context summary
                module = getattr(event, "module", None)
                ctx_keys = 0
                try:
                    # module may be a libcst.Module or None; avoid expensive ops
                    if isinstance(module, dict):
                        ctx_keys = len(module.keys())
                except Exception:
                    ctx_keys = 0
                self._log.debug(
                    "stage.post %s idx=%s id=%s duration_ms=%s ctx_keys=%s",
                    getattr(event, "stage_name", "<stage>"),
                    getattr(event, "index", 0),
                    stage_id,
                    duration_ms,
                    ctx_keys,
                )
        except Exception:
            # Never allow observer exceptions to bubble
            pass


def logging_enabled() -> bool:
    """Return True when pipeline logging is enabled via environment var.

    Truthy values: "1", "true", "True", "yes", "on".
    """

    val = os.environ.get("SPLURGE_ENABLE_PIPELINE_LOGS", "0")
    return val in ("1", "true", "True", "yes", "on")


def logging_enabled_stages() -> bool:
    """Return True when per-stage debug logging is explicitly enabled.

    Controlled by the environment variable SPLURGE_DEBUG_STAGES. Truthy
    values: "1", "true", "True", "yes", "on".
    """

    val = os.environ.get("SPLURGE_DEBUG_STAGES", "0")
    return val in ("1", "true", "True", "yes", "on")


__all__ = [
    "EventBus",
    "RecordingObserver",
    "DiagnosticsObserver",
    "LoggingObserver",
    "logging_enabled",
    "PipelineStarted",
    "PipelineCompleted",
    "StageStarted",
    "StageCompleted",
    "StageErrored",
    "TaskStarted",
    "TaskCompleted",
    "TaskSkipped",
    "TaskErrored",
]


# -----------------
# Hook infrastructure
# -----------------

Hook = Callable[..., None]


class HookRegistry:
    """Lightweight hook registry for before/after stage/task and on_error.

    Errors in hooks are isolated; unregistered hooks are no-ops.
    """

    def __init__(self) -> None:
        self._hooks: DefaultDict[str, list[Hook]] = defaultdict(list)

    def on(self, name: str, hook: Hook) -> None:
        self._hooks[name].append(hook)

    # trigger methods
    def before_stage(self, stage_name: str, context: dict[str, Any]) -> None:
        self._trigger("before_stage", stage_name, context)

    def after_stage(self, stage_name: str, result: dict[str, Any]) -> None:
        self._trigger("after_stage", stage_name, result)

    def before_task(self, stage_name: str, task_name: str, context: dict[str, Any]) -> None:
        self._trigger("before_task", stage_name, task_name, context)

    def after_task(self, stage_name: str, task_name: str, result: dict[str, Any]) -> None:
        self._trigger("after_task", stage_name, task_name, result)

    def on_error(self, where: str, exc: Exception, context: dict[str, Any]) -> None:
        self._trigger("on_error", where, exc, context)

    def _trigger(self, name: str, *args: Any) -> None:
        for hook in list(self._hooks.get(name, [])):
            try:
                hook(*args)
            except Exception:
                # do not propagate hook errors
                pass


__all__ += ["HookRegistry"]
