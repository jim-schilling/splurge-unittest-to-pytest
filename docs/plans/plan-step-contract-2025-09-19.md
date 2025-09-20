Plan: Step contract and runner stabilization (2025-09-19)

Goal
----
Stabilize a small, well-documented Step contract and ensure the `run_steps` runner conforms to it. This will serve as a solid foundation for migrating Tasks to Steps across the pipeline.

Motivation
----------
- Steps are the most granular units of transformation; a stable contract enables safe, testable migrations.
- A tested runner reduces mental overhead when converting Tasks and limits regressions.

Contract (minimal)
------------------
- Step.execute(context: Mapping[str, Any], resources: Any) -> StepResult
- StepResult: dataclass(TaskResult-like) with fields:
  - delta: ContextDelta(values: dict[str, Any])
  - diagnostics: dict[str, Any]
  - errors: list[Exception]
  - skipped: bool

Runner semantics (`run_steps`)
-----------------------------
- Accepts: stage_id, task_id, task_name, Sequence[Step], context (Mapping), resources
- Behavior:
  - Publish TaskStarted event and call hooks.before_task
  - For each Step in order:
    - Publish StepStarted (if diagnostics enabled) and call hooks.before_step
    - Invoke Step.execute
    - If Step.execute raises -> treat as error: publish StepErrored, append to errors, stop
    - If StepResult.errors is non-empty -> treat as error: publish StepErrored, append to errors, stop
    - Otherwise fold StepResult.delta into working context, aggregate non-`__tmp_step__` keys to TaskResult.delta
    - Call hooks.after_step and publish StepCompleted (if diagnostics enabled)
  - After loop: publish TaskCompleted or TaskErrored depending on errors; call hooks.after_task
  - Return TaskResult with aggregated delta, diagnostics, and errors

Transient keys
--------------
- Keys that start with `__tmp_step__` are considered transient and must not be included in returned TaskResult.delta.

Events & Hooks
--------------
- Use existing `EventBus` events: TaskStarted/TaskCompleted/TaskErrored, StepStarted/StepCompleted/StepErrored
- Use existing `HookRegistry` methods: before_task/after_task/before_step/after_step
- Runner must guard hook/event errors so they do not interrupt runner flow.

Testing
-------
Add unit tests for:
- Happy path: two Steps that produce deltas; runner folds deltas and publishes TaskStarted/TaskCompleted
- StepResult.errors path: a Step that returns a StepResult with non-empty `errors`: runner stops, publishes StepErrored/TaskErrored and returns errors
- Exception path: Step.execute raises -> runner handles as error
- Transient keys: ensure `__tmp_step__` keys do not appear in final delta
- Hooks/events: verify hooks and EventBus observers are invoked in the expected order

Migration pilot
---------------
- After runner stabilization, migrate a single Task (recommended: `assertion_rewriter`) to Steps using the new runner.
- Keep the Task wrapper and lifecycle events during the pilot to maintain backward compatibility.

Rollout & Quality gates
-----------------------
- For each migration: run `ruff --fix`, `mypy -p splurge_unittest_to_pytest`, and `pytest -n 9`.
- Keep changes small and add tests before behavioral changes where practical.

Notes
-----
- This plan intentionally keeps runtime behavior unchanged while making static typing and error-handling explicit.
- The `cast(PipelineContext, ...)` usage elsewhere in the pipeline is acceptable as a type-only coercion; prefer small comments documenting why.
