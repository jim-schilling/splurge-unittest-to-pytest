# Research: Introducing Steps into the Pipeline (2025-09-19)

## Context and current state

- The pipeline is orchestrated by `stages/manager.py:StageManager`, which executes typed stage callables that accept/return a `PipelineContext` mapping.
- Observability:
  - Event bus publishes `PipelineStarted/Completed`, `StageStarted/Completed`, and task-level events (`TaskStarted/Completed/Errored`) where stages have been taskized.
  - Hook registry provides `before_stage/after_stage/before_task/after_task/on_error` extension points.
  - Diagnostics observer can snapshot module state after each stage when enabled.
- Contracts/types (`types.py`):
  - `PipelineContext` is a permissive TypedDict for context immutability-by-convention; producers should return deltas via `ContextDelta`.
  - `Task` protocol: atomic unit with `execute(context, resources) -> TaskResult` returning a `ContextDelta`.
  - `Stage` protocol: a collection of `Task`s returning a `StageResult`.
- Current decomposition:
  - Stages such as `import_injector_stage` and `generator_stage` already orchestrate multiple `Task`s (Detect/Insert; Build/Finalize) while emitting per-task events.
  - Many other stages remain monolithic (e.g., `fixtures_stage`, `fixture_injector_stage`, `rewriter_stage`, `decorator_and_mock_fixes_stage`, etc.).

## Goal

- Introduce a new decomposition level: Step.
- Definitions (single-responsibility, pure functions over context):
  - Stage: takes context input, produces context output. No side effects; avoid mutating input; changes expressed via output delta.
  - Task: same contract, focused responsibility; composed into Stage.
  - Step: most granular unit of work; same pure contract; composed into Task.
- Rationale: Break brittle/monolithic Tasks into smaller, testable parts; improve reliability, observability, and reuse.

## Proposed Step concept

- Step protocol (new):
  - id: StepId (string), name: str.
  - execute(context: Mapping[str, Any], resources: Any) -> StepResult.
  - Returns a `ContextDelta` plus diagnostics/errors/skipped flags (mirroring `TaskResult`).
- Step invariants:
  - Pure transformation: do not mutate input context or perform external side-effects; express changes via `ContextDelta`.
  - Deterministic and idempotent given same inputs.
  - Small, cohesive logic with a single clearly named responsibility.
- Observability:
  - New events: `StepStarted`, `StepCompleted`, `StepSkipped`, `StepErrored`.
  - Hook support: `before_step`, `after_step`.

## Options to introduce Steps

### Option A: Lightweight Steps nested under existing Task protocol

- Keep the current `Task` protocol unchanged. Define a simple `Step` dataclass and have Tasks act as composite executors of Steps.
- Implementation:
  - Add types: `StepId`, `StepResult`, `Step` protocol to `types.py`.
  - Add events and hook methods to `stages/events.py` and `HookRegistry`.
  - Provide a tiny helper `run_steps(steps: Sequence[Step], context, resources) -> TaskResult` that:
    - Publishes per-step events and hooks.
    - Folds step deltas into an accumulator mapping (without mutating the original context), passing an updated working copy to subsequent steps.
    - Aggregates diagnostics/errors into the `TaskResult`.
  - Refactor monolithic Tasks to a thin coordinator that lists Steps in order and delegates to `run_steps`.
- Pros:
  - Minimal surface area change; preserves Task and Stage contracts.
  - Incremental migration: refactor one Task at a time.
  - Retains existing pipeline wiring; no StageManager changes required.
- Cons:
  - StageManager is unaware of Steps (only Tasks), though events/hooks provide visibility.

### Option B: First-class Steps in the manager (StageManager executes Steps)

- Elevate Steps into StageManager with three-level execution: Stage -> Task -> Step orchestrated centrally.
- Implementation:
  - Extend `StageManager` to detect Task containers, iterate their Steps, publish Step events, and merge deltas.
  - Tasks become declarative containers (metadata + step list) rather than imperative executors.
- Pros:
  - Uniform orchestration and consistent diagnostics across all levels.
  - Centralized merge semantics and error handling.
- Cons:
  - Larger refactor touching StageManager and every Task implementation.
  - Higher risk for regressions in pipeline execution.

### Option C: Task-only world, but enforce micro-Tasks instead of Steps

- Do not add a new concept. Decompose monolithic Tasks into multiple small Tasks and treat them as Steps conceptually.
- Pros:
  - Zero new abstractions.
  - Full visibility already exists via task events.
- Cons:
  - Task taxonomy becomes very fine-grained, potentially bloating Stage code and logs.
  - Misses ergonomic reuse at the Task-internal level.

## Merge semantics and purity

- Keep the existing pattern: each unit produces a `ContextDelta`, the orchestrator folds deltas left-to-right.
- Units should read from a read-only view of the current working context and not mutate it in-place.
- Steps within a Task receive the evolving working copy (context + prior deltas) to avoid hidden dependencies.

## Error handling

- On Step error:
  - Publish `StepErrored`; Task may either accumulate and continue (if safe) or fail-fast and return with errors.
  - For safety and determinism, default to fail-fast in early adoption; consider opt-in continue-on-error for diagnostic runs.

## Testing strategy

- Unit-test each Step with minimal context fixtures, verifying:
  - Delta contents and no mutation of input.
  - Idempotency: running twice yields the same outcome.
- Unit-test Task coordinators to ensure step ordering and delta folding are correct.
- Integration tests remain at Stage and pipeline level (unchanged).

## Candidate refactors (shortlist)

- `generator_tasks.BuildFixtureSpecsTask`:
  - Steps: collect_used_names, precompute_bundling_full, build_specs_per_class, infer_filenames_in_calls, select_yield_style, emit_fixture_nodes, mark_needs_shutil, add_bundling_wrappers.
- `import_injector_tasks.DetectNeedsCstTask`:
  - Steps: seed_flags_from_context, scan_module_text_for_usages, compute_typing_needs.
- `import_injector_tasks.InsertImportsCstTask`:
  - Steps: determine_insert_index, collect_existing_imports, compute_required_nodes, apply_preferred_ordering, dedupe_against_existing, insert_nodes, prune_unused_typing.
- Other monolithic stages (future): `fixtures_stage`, `fixture_injector_stage`, `rewriter_stage`, `decorator_and_mock_fixes_stage`, `tidy_stage`.

## Recommendation

- Prefer Option A (Lightweight Steps inside Tasks) for incremental, low-risk adoption.
  - Reasoning:
    - Aligns with the existing partial taskization pattern already present in `import_injector_stage` and `generator_stage`.
    - Minimal changes to the pipeline runner and stage APIs.
    - Enables immediate decomposition of brittle Tasks without a manager refactor.

## Minimal specification (Option A)

1) Types (`types.py`):

```python
# New identifiers and results
StepId = str

@dataclass(frozen=True)
class StepResult:
    delta: ContextDelta
    diagnostics: dict[str, Any] = field(default_factory=dict)
    errors: list[Exception] = field(default_factory=list)
    skipped: bool = False

class Step(Protocol):
    id: StepId
    name: str
    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult: ...
```

2) Events and hooks (`stages/events.py`):

```python
@dataclass(frozen=True)
class StepStarted: ...
@dataclass(frozen=True)
class StepCompleted: ...
@dataclass(frozen=True)
class StepSkipped: ...
@dataclass(frozen=True)
class StepErrored: ...

# HookRegistry additions
def before_step(self, task_name: str, step_name: str, context: dict[str, Any]) -> None: ...
def after_step(self, task_name: str, step_name: str, result: dict[str, Any]) -> None: ...
```

3) Helper (`stages/adapters.py` or a new `steps.py`):

```python
def run_steps(task_id: str, task_name: str, steps: Sequence[Step], context: Mapping[str, Any], resources: Any, bus: EventBus | None, hooks: HookRegistry | None) -> TaskResult:
    working = dict(context)
    agg_delta: dict[str, Any] = {}
    errors: list[Exception] = []
    diagnostics: dict[str, Any] = {}
    for step in steps:
        if isinstance(bus, EventBus):
            bus.publish(StepStarted(run_id="", stage_id=task_id, task_id=task_id, step_id=step.id))
        if hooks is not None:
            try:
                hooks.before_step(task_name, step.name, dict(working))
            except Exception:
                pass
        try:
            res = step.execute(working, resources)
            agg_delta.update(res.delta.values)
            working.update(res.delta.values)
            if hooks is not None:
                try:
                    hooks.after_step(task_name, step.name, dict(res.delta.values))
                except Exception:
                    pass
            if isinstance(bus, EventBus):
                bus.publish(StepCompleted(run_id="", stage_id=task_id, task_id=task_id, step_id=step.id))
        except Exception as exc:
            errors.append(exc)
            if isinstance(bus, EventBus):
                bus.publish(StepErrored(run_id="", stage_id=task_id, task_id=task_id, step_id=step.id, error=exc))
            break
    return TaskResult(delta=ContextDelta(values=agg_delta), diagnostics=diagnostics, errors=errors)
```

4) Adoption example (inside `BuildFixtureSpecsTask.execute`):

- Replace the current monolith with a list of Steps implementing the sub-responsibilities above and delegate to `run_steps`.

## Migration plan

- Stage 1: Introduce types/events/hooks and helper. No behavior change.
- Stage 2: Pilot convert `import_injector_tasks` to Steps; compare outputs with goldens.
- Stage 3: Convert `generator_tasks.BuildFixtureSpecsTask` to Steps; ensure parity with existing tests.
- Stage 4: Expand to other heavy tasks (fixtures, rewriter, tidy) incrementally.
- Stage 5: Optionally revisit StageManager for first-class Step orchestration once coverage is broad and stable.

## Acceptance criteria

- No change in pipeline outputs across the golden test corpus with diagnostics disabled.
- Per-step events appear in the event stream for pilot tasks; hooks fire correctly.
- Steps are unit-testable in isolation and demonstrate input immutability and idempotency.

## Risks and mitigations

- Risk: Event/hook noise. Mitigation: keep Step events opt-in via env flag, or sample only when diagnostics enabled.
- Risk: Over-fragmentation. Mitigation: keep steps cohesive and meaningful (5–25 LOC typical), avoid trivial steps.
- Risk: Implicit ordering bugs. Mitigation: unit-test task coordinators and use deterministic step lists.

## Conclusion

Adopt Option A to introduce Steps beneath Tasks, enabling granular, pure, testable units of work without disrupting the manager. Proceed with pilots in `import_injector_tasks` and `generator_tasks`, then expand.
