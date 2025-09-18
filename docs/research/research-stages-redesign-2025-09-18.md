Title: Stages and Tasks Redesign — contracts, extensibility, and testability (2025-09-18)

Purpose
- Research and evaluate options for a major redesign of the staged pipeline so that all stages and tasks adhere to standard contracts, support pre-/post-processors, visitors, observers, and structured logging/telemetry. Recommend a preferred approach and outline a phased migration plan that simplifies stage management and improves testability.

Scope and context
- Repo context: the pipeline currently uses `StageManager` to run a sequence of typed stage callables that accept and return a `PipelineContext` mapping. Diagnostics snapshots are optionally emitted between stages. Core stages include `collector`, `generator`, `rewriter`, `fixtures_stage`, `fixture_injector`, `decorator_and_mock_fixes`, `import_injector`, `postvalidator`, `raises_stage.exceptioninfo_normalizer`, and `tidy`.
- Goals: unify contracts, add clear lifecycle hooks and observation, enable optional pre/post handlers, and introduce a first-class “task” concept within a stage to improve modularity and testability.

High-level requirements
- Contract standardization
  - Every Stage and Task must implement a stable, typed interface: input is a `PipelineContext`, output is a delta plus metadata, with explicit error and metrics surfaces.
  - Standard identifiers (stable `stage_id`, `task_id`) and versioning for traceability.
- Extensibility
  - Hooks for pre- and post-processing at both stage and task granularity.
  - Observers (event subscribers) for lifecycle events (start, end, error, skip).
  - Support “visitors” as first-class Task types that operate on `libcst.Module`.
- Observability
  - Structured logging events with consistent schemas.
  - Optional tracing spans for stages and tasks.
  - Deterministic diagnostics snapshots.
- Testability
  - Unit-test Stage and Task in isolation with in-memory contexts and event collectors.
  - Deterministic execution order, pure functions preferred (returning deltas) with safe merging.
- Backwards compatibility
  - Preserve current `StageManager` external API initially; introduce adapters.

Current state snapshot (as of 2025-09-18)
- Manager
  - `StageManager` runs a list of callables with signature `StageCallable = Callable[[PipelineContext], PipelineContext]`.
  - Diagnostics can write source snapshots between stages; failures in diagnostics are ignored to not break the pipeline.
- Context
  - `PipelineContext` is a `TypedDict(total=False)` used to share `module` and flags like `needs_pytest_import`, `fixture_nodes`, etc.
- Stages
  - Multiple stages operate sequentially and either mutate the context in place or return updates that are merged.
  - Visitors/transformers are used inside stages (e.g., `libcst` passes).

Design options

Option A — Strengthen current model with formal Stage/Task contracts (preferred foundation)
- Summary
  - Keep `StageManager` sequencing but formalize interfaces and lifecycle. Introduce a `Stage` protocol and a `Task` protocol. Each Stage composes Tasks; Manager runs Stages and emits typed lifecycle events. Pre-/post-processors are simply hook chains invoked around stage/task execution.
- Pros
  - Minimal disruption, preserves current mental model and ordering.
  - Enables unit testing at Task granularity; clearer contracts and metrics.
  - Straightforward integration of visitors by defining a `CstTask` specialization.
- Cons
  - Still single-threaded/linear; parallelism is out-of-scope unless later extended.
- Fit
  - Best alignment with existing code while unlocking testability and extensibility.

Option B — Middleware/Chain-of-Responsibility around stages
- Summary
  - Wrap each stage call in a configurable middleware chain providing before/after processing and observation. Tasks remain internal to stages.
- Pros
  - Very simple to add cross-cutting behavior; limited changes.
- Cons
  - Tasks remain implicit; weaker test surface; less structured events.
- Fit
  - Good short-term increment but does not meet “tasks as first-class” goal.

Option C — Pluggy-powered hook system (pytest-style plugins)
- Summary
  - Define hook specs (e.g., `stage_start`, `task_end`, `on_error`) and use `pluggy` to allow external/internal plugins to subscribe. Stages/tasks call into hooks at key points.
- Pros
  - Mature, widely used by pytest; excellent extension story without tight coupling.
- Cons
  - Another dependency; hook calling surfaces must stay stable; some complexity in testing if overused.
- Fit
  - Strong candidate for observation and optional pre/post processors; pairs well with Option A.

Option D — Event bus with typed observers (pub/sub)
- Summary
  - Introduce a small internal event bus for typed events (`StageStarted`, `TaskCompleted`, etc.). Observers can subscribe, including logging, metrics, and snapshot writers.
- Pros
  - Decoupled, easy to test, no external dependency required.
- Cons
  - Less feature-rich than `pluggy`; need to design subscription and error isolation.
- Fit
  - Good internal mechanism; can coexist with `pluggy` (bus publishes, a pluggy plugin subscribes).

Option E — SEDA/async queues between stages
- Summary
  - Decompose into asynchronous stages connected by queues for scalability.
- Pros
  - High throughput, isolation.
- Cons
  - Overkill for a deterministic source-to-source transform; adds complexity and async concerns.
- Fit
  - Not recommended for this project’s needs.

Observability options
- Structured logging
  - `structlog` for domain-keyed events; or stdlib logging with JSON formatter.
  - Recommend `structlog` for developer ergonomics and consistent event dictionaries.
- Tracing
  - OpenTelemetry Python to create spans per stage/task. Exporters can be no-op, console, OTLP.
  - Attributes: `pipeline.run_id`, `stage.id`, `stage.version`, `task.id`, `elapsed_ms`, `outcome`.
- Diagnostics
  - Keep existing snapshots, move under an observer, indexed by event sequence numbers.

Proposed contracts (concrete)

Types (abridged)
```python
from dataclasses import dataclass, field
from typing import Protocol, Mapping, MutableMapping, Any, Sequence

StageId = str
TaskId = str

class Resources(Protocol):
    logger: Any
    tracer: Any  # OpenTelemetry Tracer or NoOp
    hooks: Any   # pluggy or internal bus adapter
    clock: Any

@dataclass(frozen=True)
class ContextDelta:
    values: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class TaskResult:
    delta: ContextDelta
    diagnostics: dict[str, Any] = field(default_factory=dict)
    errors: list[Exception] = field(default_factory=list)
    skipped: bool = False

class Task(Protocol):
    id: TaskId
    name: str
    def execute(self, context: Mapping[str, Any], resources: Resources) -> TaskResult: ...

@dataclass(frozen=True)
class StageResult:
    delta: ContextDelta
    diagnostics: dict[str, Any] = field(default_factory=dict)
    errors: list[Exception] = field(default_factory=list)

class Stage(Protocol):
    id: StageId
    version: str
    name: str
    tasks: Sequence[Task]
    def execute(self, context: Mapping[str, Any], resources: Resources) -> StageResult: ...
```

Execution semantics
- Manager initializes a `Resources` bundle (logger, tracer, hooks/bus, clock) and emits `PipelineStarted`.
- For each Stage:
  - Emit `StageStarted`; run pre-processors via hooks (`before_stage`), then `Stage.execute`.
  - Inside `Stage.execute`, iterate tasks: for each task, emit `TaskStarted`, run pre-task hooks, execute, run post-task hooks, emit `TaskCompleted`.
  - Merge `TaskResult.delta` values into a new mapping, never mutating the original context in place. Explicit rule: only the manager writes the resulting merged context, and `module` replacements are treated as atomic updates.
  - Emit `StageCompleted` with metrics and errors.
- Any exception is captured, emitted as an error event, and the manager decides policy (continue or abort). For this pipeline, continue with best-effort unless stage declares `fatal=True`.

First-class visitors
- Define `CstTask(Task)` helper that:
  - Reads `module` from context, applies a `libcst.CSTTransformer` or visitor, returns a `TaskResult` with the new module and any flags (`needs_pytest_import`, etc.).
  - Encourages micro-transformers that are easy to unit test.

Pre-/post-processors
- Define hook points:
  - `before_stage(stage, context) -> None`
  - `after_stage(stage, result) -> None`
  - `before_task(stage, task, context) -> None`
  - `after_task(stage, task, result) -> None`
  - `on_error(stage|task, exc, context) -> None`
- Implementation choices:
  - Lightweight internal bus with subscriber registration, or
  - `pluggy` with a small `hookspec` module for stable interfaces.

Observers and logging
- Event types
  - `PipelineStarted`, `PipelineCompleted`
  - `StageStarted`, `StageCompleted`, `StageErrored`
  - `TaskStarted`, `TaskCompleted`, `TaskSkipped`, `TaskErrored`
- Provide built-in observers:
  - `LoggingObserver` (structlog): writes structured events with context keys.
  - `TracingObserver` (OpenTelemetry): creates spans with attributes.
  - `DiagnosticsObserver`: writes intermediate module snapshots using event sequence numbers.

Testing strategy
- Provide `StageTestHarness` and `TaskTestHarness` utilities:
  - Build minimal `PipelineContext` fixtures and a `RecordingObserver` for assertions.
  - Assert that running a task produces an expected delta and events without touching disk.
- Prefer tasks that are pure functions from context to delta (with explicit errors/diagnostics) for easy unit testing.

Trade-offs and considerations
- Context mutation vs deltas: adopting deltas reduces shared-state bugs and clarifies ownership, at the cost of shallow copies. For large `module` objects, updates remain by reference replacement.
- Hook overhead: negligible under Python; guard with a “no-op” fast path if no observers installed.
- Type rigor: continue `TypedDict(total=False)` for `PipelineContext`, but use dataclasses and `Protocol` for contracts to improve clarity without constraining stage internals early.

Preferred recommendation
- Adopt Option A (formal Stage/Task contracts) as the foundation, and integrate Option C/D for hooks/observers:
  - Keep current `StageManager` while introducing a new `StageRunner` inside it that knows how to run `Stage` objects and emit events.
  - Add a small internal event bus first; optionally expose `pluggy` integration later by adapting bus events to hook calls.
  - Introduce `CstTask` to make libcst operations uniform and testable.
  - Use `structlog` for structured logs by default; add optional OpenTelemetry spans (no-op by default) for future-proof tracing.

Phased migration plan (low-risk)
- Stage-0: Contracts and scaffolding (no behavior change)
  - Add new types to `splurge_unittest_to_pytest/types.py`: `ContextDelta`, `TaskResult`, `StageResult`, `Task`/`Stage` Protocols, and typed event classes.
  - Add `events.py` with a minimal in-process event bus and observer interfaces.
  - Wire `StageManager` to create a `Resources` bundle and expose an internal `emit` API; keep existing callable stages working through an adapter `CallableStage` that wraps legacy functions as a single-task stage.
- Stage-1: Observers and diagnostics
  - Move diagnostics snapshots behind a `DiagnosticsObserver`. Add `LoggingObserver` (structlog).
  - Gate observers behind a CLI/env flag (defaults to minimal logging).
- Stage-2: Introduce tasks in one stage (pilot)
  - Split `import_injector` or `raises_stage.exceptioninfo_normalizer` into 2–3 `CstTask`s. Add targeted unit tests with the `TaskTestHarness`.
- Stage-3: Hook system
  - Add internal hook points and adapters. Consider optional `pluggy` support with a small `hookspec` module so third-parties can extend behavior without forking.
- Stage-4: Broader refactor
  - Gradually convert additional stages into composed `Task`s, focusing on those with distinct, testable sub-steps (e.g., generator subtasks already exist under `generator_parts`).
  - Document stable stage IDs and versioning; update reporting to include per-stage metrics.
- Stage-5: Cleanup
  - Deprecate direct context mutation in favor of deltas for all core stages.
  - Finalize documentation of contracts and observer APIs.

Acceptance criteria
- All existing tests pass throughout migrations; new unit tests cover `Task` and `Observer` behavior.
- Structured events are emitted deterministically with stable schemas.
- Diagnostics snapshots are produced via observers and are identical (or improved) relative to current behavior when enabled.
- Minimal performance overhead when observers/tracing are disabled.

Risks and mitigations
- Scope creep: constrain Stage-0/1 to pure scaffolding; no functional changes.
- Plugin API churn: version hook specs and event schemas and keep them additive.
- Performance: use fast no-op observers by default; lazy creation of spans.

Open questions
- Do we want a formal JSON schema for events for external tooling? Proposed later when `--json` pipeline logs graduate from experimental.
- Should Task errors abort Stage by default, or accumulate and continue? Proposed: continue by default and mark stage outcome as degraded unless `fatal=True`.

Appendix — example minimal adapter
```python
class CallableStage:
    def __init__(self, stage_id: str, fn: StageCallable):
        self.id = stage_id
        self.version = "1"
        self.name = fn.__name__
        self.tasks = (self._TaskAdapter(fn),)

    class _TaskAdapter:
        def __init__(self, fn):
            self.id = f"task:{fn.__name__}"
            self.name = fn.__name__
            self._fn = fn
        def execute(self, context, resources):
            try:
                result = self._fn(context)  # legacy behavior
                return TaskResult(delta=ContextDelta(values=dict(result)))
            except Exception as exc:
                resources.hooks.on_error(stage=None, exc=exc, context=context)
                return TaskResult(delta=ContextDelta(values={}), errors=[exc])
```

Recommendation summary
- Implement Stage/Task contracts with a delta-based merge model.
- Add lifecycle events with internal bus; optionally integrate `pluggy` for third-party hooks.
- Provide `CstTask` for visitor-based transformations.
- Adopt `structlog` for logging and optional OpenTelemetry spans for tracing.
- Migrate in phases with adapters to avoid breaking changes and to steadily improve testability.


