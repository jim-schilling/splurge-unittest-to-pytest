"""Type definitions for pipeline contexts and shared stage structures.

Small, stable TypedDicts and aliases used by pipeline stages. Introduced in
2025.2.0 as part of the Stage-1 refactor to make stage contexts explicit and
typed for future refactors.

Public:
    PipelineContext
    TextWriterProtocol

Copyright (c) 2025 Jim Schilling
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Protocol, Sequence, TypedDict

DOMAINS = ["types", "pipeline"]


class PipelineContext(TypedDict, total=False):
    """TypedDict for passing state between stages in the conversion pipeline.

    Fields are intentionally permissive (total=False) to allow incremental
    migration; stages should document which keys they read/write.

    Common keys:
        module: libcst.Module - the current Module being transformed
        autocreate: bool - whether to autocreate tmp-backed fixtures
        pattern_config: Any - optional pattern configuration for method matching
        collector_output: Any - output produced by the Collector stage
    """

    module: Any
    autocreate: bool
    pattern_config: Any
    collector_output: Any
    # Common stage outputs
    needs_pytest_import: bool
    needs_re_import: bool
    needs_unittest_import: bool
    needs_sys_import: bool
    needs_os_import: bool
    needs_shutil_import: bool
    needs_typing_names: Any
    fixture_nodes: Any
    postvalidator_error: Any
    # Pipeline flag to request normalization of fixture names (strip leading underscores)
    normalize_names: bool
    # Internal stage identifier for step/task event binding
    __stage_id__: str


__all__ = ["PipelineContext"]


# Protocol for text-like writers used by io_helpers.safe_file_writer
class TextWriterProtocol(Protocol):
    """Protocol describing minimal text-writer interface used in package.

    This mirrors the small subset of io.TextIO used by the safe atomic
    writer: write/writelines/flush/close and context-manager methods.
    """

    def write(self, data: str) -> int: ...

    def writelines(self, lines: Iterable[str]) -> None: ...

    def flush(self) -> None: ...

    def close(self) -> None: ...

    def __enter__(self) -> "TextWriterProtocol": ...

    def __exit__(
        self,
        exc_type: Optional[type],
        exc: Optional[BaseException],
        tb: Optional[Any],
    ) -> Optional[bool]: ...


__all__.append("TextWriterProtocol")


# --------------------
# Stage/Task contracts
# --------------------

# Stable identifiers for stages and tasks
StageId = str
TaskId = str


@dataclass(frozen=True)
class ContextDelta:
    """Represents changes produced by a Task or Stage.

    Keys are merged into the pipeline context by the manager. The manager owns
    merge semantics; producers return deltas and should avoid mutating the input
    context in place when practical.
    """

    values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskResult:
    """Result of executing a single Task."""

    delta: ContextDelta
    diagnostics: dict[str, Any] = field(default_factory=dict)
    errors: list[Exception] = field(default_factory=list)
    skipped: bool = False


@dataclass(frozen=True)
class StageResult:
    """Aggregated result of executing a Stage (composed of Tasks)."""

    delta: ContextDelta
    diagnostics: dict[str, Any] = field(default_factory=dict)
    errors: list[Exception] = field(default_factory=list)


class Task(Protocol):
    """Task protocol for first-class, testable pipeline steps."""

    id: TaskId
    name: str

    # A Task may be composed of one or more Steps. Expose the underlying
    # Step instances (or an empty sequence) for tooling and runtime
    # introspection. Implementations may provide an explicit list or an
    # empty sequence when they perform their work directly.
    steps: Sequence["Step"]

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult: ...


class Stage(Protocol):
    """Stage protocol composed of multiple Tasks."""

    id: StageId
    version: str
    name: str
    tasks: Sequence[Task]

    def execute(self, context: Mapping[str, Any], resources: Any) -> StageResult: ...


__all__ += [
    "StageId",
    "TaskId",
    "ContextDelta",
    "TaskResult",
    "StageResult",
    "Task",
    "Stage",
]


class Resources(Protocol):
    """Resources passed to stages/tasks (logger, tracer, hooks, clock).

    Protocol-only for Stage-0. Implementations are provided by the manager.
    """

    logger: Any
    tracer: Any
    hooks: Any
    clock: Any


__all__.append("Resources")


# --------------------
# Step contracts
# --------------------

# Stable identifier for steps
StepId = str


@dataclass(frozen=True)
class StepResult:
    """Result of executing a single Step."""

    delta: ContextDelta
    diagnostics: dict[str, Any] = field(default_factory=dict)
    errors: list[Exception] = field(default_factory=list)
    skipped: bool = False


class Step(Protocol):
    """Step protocol: most granular, pure context transformation unit."""

    id: StepId
    name: str

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult: ...


__all__ += [
    "StepId",
    "StepResult",
    "Step",
]
