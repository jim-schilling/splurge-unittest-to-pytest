Title: Developer Spec — Stages Contracts, Tasks, Observers, and Hooks (2025-09-18)

Purpose
- Establish concrete guidelines for implementing stages and tasks, using the delta-based `PipelineContext`, and integrating observers and hooks. This complements the research and plan documents.

Scope
- Applies to code under `splurge_unittest_to_pytest/stages/` and shared types in `splurge_unittest_to_pytest/types.py`.

Contracts
- PipelineContext: A permissive TypedDict (total=False). Stages read keys, and produce changes via ContextDelta.
- Delta model: Stages/Tasks return `TaskResult/StageResult` with `ContextDelta(values=...)`. Do not mutate the incoming context in place.
- Identifiers: Use stable semantic IDs (`stages.import_injector`, `tasks.import_injector.detect_needs`) and version per stage (`STAGE_VERSION`).

Tasks
- Implement the `Task` protocol’s `execute(context, resources) -> TaskResult`.
- Keep tasks small and single-purpose; prefer pure transformations.
- For LibCST transforms, prefer visitor/transformers in task-specific modules (e.g., `*_tasks.py`).
- Testing: Use `tests/support/task_harness.py::TaskTestHarness` for unit tests with minimal contexts.

Stages
- A stage composes tasks and aggregates their deltas into the pipeline context.
- Emit per-task events: `TaskStarted/TaskCompleted/TaskSkipped/TaskErrored` via `EventBus` when available.
- Include `STAGE_ID`, `STAGE_VERSION`, and `name`.

Observers and Diagnostics
- Observers subscribe to lifecycle events published to `EventBus`.
- `DiagnosticsObserver`: writes deterministic snapshots (module code, stage/task markers).
- `LoggingObserver`: structured logging gated by environment.
- Enable logging via env var: `SPLURGE_ENABLE_PIPELINE_LOGS=1` (default off). Diagnostics are controlled by the manager’s diagnostics toggle.

Hooks
- Hook registry supports: `before_stage/after_stage`, `before_task/after_task`, and `on_error`.
- Hooks are invoked with copies of context/deltas to avoid accidental mutation.
- Keep hook logic side-effect constrained; errors in hooks must be isolated and not fail the pipeline.

CLI and Controls
- Logging: set `SPLURGE_ENABLE_PIPELINE_LOGS=1` to enable `LoggingObserver` output.
- Diagnostics: when diagnostics are enabled by the manager, `DiagnosticsObserver` writes snapshots to the configured directory.
- No public CLI flags are currently exposed for observers; use the env var for logs. Future work may add flags if needed.

Implementation Notes
- Avoid direct `context[...] = ...` or `context.update(...)` in stages/tasks. Use `ContextDelta` exclusively.
- Return types from stages should be `PipelineContext` (cast as needed for mypy).
- Prefer deterministic ordering for generated nodes and imports.

Acceptance
- All migrated stages follow these rules; tests verify per-task events, diagnostics snapshots, and hook behavior.


