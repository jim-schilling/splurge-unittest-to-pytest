# Plan: Implement Steps (Option A) — 2025-09-19

Reference: See research doc `docs/research/research-steps-2025-09-19.md` for analysis, options, and recommendation.

## Objective

Introduce Steps as the most granular, pure unit under Tasks, enabling decomposition of brittle Tasks, improved testability, and richer observability, with minimal disruption to StageManager and existing stages.

## Scope and non-goals

- In scope: Step types/results, Step events/hooks, helper to orchestrate Steps inside existing Tasks, incremental refactors of target Tasks.
- Out of scope (for Option A): Changing StageManager to be Step-aware; altering Stage contracts.

## Guiding principles

- Purity: Steps do not mutate input context nor produce side effects; return `ContextDelta`.
- Determinism: Given same inputs, Steps are idempotent and predictable.
- Cohesion: Each Step has a single responsibility and descriptive `id`/`name`.
- Observability: Per-step events and hooks are emitted; can be gated by env flags to reduce noise.

## Deliverables

- New types in `types.py`: `StepId`, `StepResult`, `Step` protocol.
- New events in `stages/events.py`: `StepStarted`, `StepCompleted`, `StepSkipped`, `StepErrored`.
- Hook additions in `HookRegistry`: `before_step`, `after_step`.
- `run_steps` helper (e.g., `stages/adapters.py` or `stages/steps.py`).
- Pilot refactors: `import_injector_tasks` and `generator_tasks`.
- Unit tests for Steps and task coordinators, plus golden stability verification.

## Acceptance criteria

- No diffs in golden outputs with diagnostics disabled across pilot conversions.
- Step events emitted for pilot tasks and hooks invoked in order.
- Steps unit-tested for purity and idempotency.
- CLI/Stage APIs unchanged; existing integrations unaffected.

## Step contract (minimal)

- Step.execute(context: Mapping[str, Any], resources: Any) -> StepResult
- StepResult (dataclass) with fields:
  - delta: ContextDelta(values: dict[str, Any])
  - diagnostics: dict[str, Any]
  - errors: list[Exception]
  - skipped: bool

Steps should be pure (avoid mutating the input context in-place) and return a ContextDelta describing only the keys they intend to change.

## Runner semantics (`run_steps`)

- Accepts: stage_id, task_id, task_name, Sequence[Step], context (Mapping), resources
- Behavior:
  - Publish TaskStarted event and call hooks.before_task.
  - For each Step in order:
    - Publish StepStarted (if diagnostics enabled) and call hooks.before_step.
    - Invoke Step.execute.
    - If Step.execute raises -> treat as error: publish StepErrored, append to errors, stop.
    - If StepResult.errors is non-empty -> treat as error: publish StepErrored, append to errors, stop.
    - Otherwise fold StepResult.delta into the working context (but do not include transient keys in the final delta).
    - Call hooks.after_step and publish StepCompleted (if diagnostics enabled).
  - After loop: publish TaskCompleted or TaskErrored depending on errors; call hooks.after_task.
  - Return TaskResult with aggregated delta (ContextDelta), diagnostics, and errors.

Transient keys
--------------

- Keys that begin with `__tmp_step__` are considered transient and must not be present in the returned TaskResult.delta.

Events & Hooks
--------------

- Use existing EventBus events: TaskStarted/TaskCompleted/TaskErrored, StepStarted/StepCompleted/StepErrored.
- Use HookRegistry methods: before_task/after_task/before_step/after_step.
- Runner must guard against exceptions from hooks/events so they do not interrupt the runner flow.

Testing (required unit tests for the runner)
-----------------------------------------

- Happy path: two Steps producing deltas — runner folds deltas and publishes TaskStarted/TaskCompleted.
- StepResult.errors path: a Step returns a StepResult with non-empty `errors` — runner stops and returns errors.
- Exception path: Step.execute raises — runner handles the exception, publishes StepErrored/TaskErrored.
- Transient keys: ensure `__tmp_step__` keys do not appear in final delta.
- Hooks/events: verify hooks and EventBus observers are invoked in the expected order.

Migration pilot
---------------

- After stabilizing the runner, migrate one Task end-to-end as a pilot to validate the contract and the rollout path. Recommended pilot tasks (in descending order):
  1. `assertion_rewriter` (already piloted) — verify parity and keep compatibility Step if needed.
  2. `raises_stage` — high impact (imports/pytest) and a good next candidate.

Rollout & Quality gates (extended)
----------------------------------

- For each migration: run `ruff --fix`, `mypy -p splurge_unittest_to_pytest`, and `pytest -n 9` locally before opening a PR.
- Keep PRs small where possible; add Step unit tests first, then integration/task-level tests, then run golden checks.
- If a Step's behavior is uncertain, provide a compatibility Step that delegates to the legacy transformer until parity is proven in tests/CI.


## Rollout plan (phased)

### Phase 1 — Foundations (types, events, hooks, helper)

- Tasks
  - Add `StepId`, `StepResult`, `Step` to `types.py`.
  - Add `StepStarted/Completed/Skipped/Errored` events to `stages/events.py`.
  - Add `before_step/after_step` methods to `HookRegistry`.
  - Implement `run_steps` helper with delta folding, events, and hooks.
- Checklist
  - [x] Compile and run unit tests.
  - [x] Verify no lints introduced.
  - [x] Behind env flag: optional suppression of Step events when diagnostics off.

### Phase 2 — Pilot: import_injector_tasks

- Tasks
  - Extract Steps for `DetectNeedsCstTask`:
    - `seed_flags_from_context_step`
    - `scan_module_text_usages_step`
    - `finalize_detect_needs_step`
  - Extract Steps for `InsertImportsCstTask`:
    - `determine_insert_index_step`
    - `collect_existing_imports_step`
    - `compute_required_nodes_step`
    - `order_and_dedupe_nodes_step`
    - `insert_nodes_step`
    - `prune_unused_typing_step`
  - Replace internal imperative bodies with `run_steps` composition.
- Checklist
  - [x] Add unit tests for each Step (happy path + edge cases).
  - [x] Ensure per-task events still fire; confirm additional per-step events.
  - [x] Golden corpus: no diffs.

### Phase 3 — Pilot: generator_tasks.BuildFixtureSpecsTask

- Tasks (example Step breakdown)
  - `collect_used_names_step`
  - `precompute_bundling_full_step`
  - `build_specs_per_class_step`
  - `infer_filenames_in_calls_step`
  - `select_yield_style_step`
  - `emit_fixture_nodes_step`
  - `mark_needs_shutil_step`
  - `add_bundling_wrappers_step`
- Checklist
  - [x] Step unit tests for representative inputs.
  - [x] Task-level tests for ordering and delta folding.
  - [x] Golden corpus: no diffs.

### Phase 4 — Extend to additional Tasks

- Candidates
  - `fixtures_stage_tasks.py` / `fixtures_stage.py`
  - `fixture_injector_tasks.py`
  - `rewriter_tasks.py`
  - `decorator_and_mock_fixes_tasks.py`
  - `tidy_tasks.py`
- Checklist (per module converted)
  - [ ] Identify cohesive Steps and define stable `id`/`name`.
  - [ ] Add unit tests and wire with `run_steps`.
  - [ ] Golden corpus: no diffs.

### Phase 5 — Hardening and documentation

- Tasks
  - Document Step guidelines and examples in `docs/README-DETAILS.md` or a new `docs/specs/spec-steps.md`.
  - Add tracing/diagnostic summaries for Step counts and durations (optional).
  - Review logs for noise; gate with env flags if needed.
- Checklist
  - [ ] Documentation merged and linked from existing specs.
  - [ ] CI verifies unit + integration + goldens.

## Detailed task list (prioritized)

1. Foundations
   - [x] Implement Step types/results in `types.py`.
   - [x] Implement Step events in `stages/events.py`.
   - [x] Add HookRegistry methods for steps.
   - [x] Create `run_steps` helper and tests.
2. Pilot A: import injector
   - [x] Refactor `DetectNeedsCstTask` to Steps + tests.
   - [x] Refactor `InsertImportsCstTask` to Steps + tests.
3. Pilot B: generator
   - [x] Refactor `BuildFixtureSpecsTask` to Steps + tests.
   - [x] Refactor `FinalizeGeneratorTask` to small Step + tests.
4. Broader rollout
   The following modules are recommended next conversions. Each bullet below is an actionable checklist item you can convert independently or batch in small PRs.

   - fixtures_stage
     - [x] Confirm `stages/fixtures_stage_tasks.py` already exposes Steps (`CollectClassesStep`, `BuildTopLevelFnsStep`).
     - [ ] Add unit tests (if missing) that assert task-level delta folding and idempotency.
     - [ ] Split large Steps into smaller focused Steps where helpful.

   - fixture_injector
     - [x] Task already delegates to Steps (`FindInsertionIndexStep`, `InsertNodesStep`, `NormalizeAndPostprocessStep`).
     - [ ] Verify and add focused Step unit tests and golden checks.

   - rewriter (rewriter_tasks.py)
     - [x] Task already uses `RewriteMethodParamsStep` for method param rewriting.
     - [ ] Identify remaining monolithic rewriter functions and convert to Steps (e.g., param normalization, decorator rewrites).
     - [ ] Add unit tests for each new Step and integration tests for the task.

   - raises stage (raises_stage_tasks.py) — recommended first NEW migration
     - [ ] Create `ParseRaisesStep` (validate module present).
     - [ ] Create `TransformRaisesStep` (apply `RaisesRewriter` -> return module + `needs_pytest_import`).
     - [ ] Create `NormalizeExceptionAttrStep` (run `ExceptionAttrRewriter` for collected names).
     - [ ] Add unit tests for each Step and an integration test asserting `run_steps` merges `needs_pytest_import` into TaskResult.delta.
     - [ ] Gate release with golden tests and CI full-suite to ensure parity.

   - remove_unittest_artifacts (remove_unittest_artifacts_tasks.py)
     - [ ] Extract `RemoveUnittestArtifactsStep` (transformer logic -> Step.execute returning module delta).
     - [ ] Add unit tests for common patterns (import removal, TestCase base removal, __main__ cleanup).

   - postvalidator (postvalidator_tasks.py)
     - [ ] Wrap existing validation in `ValidateModuleStep` (small, low-risk Step).
     - [ ] Add tests that validation errors are surfaced in TaskResult.delta as `postvalidator_error`.

   - decorator_and_mock_fixes (decorator_and_mock_fixes_tasks.py)
     - [x] Task already wraps `ApplyDecoratorAndMockFixesStep`.
     - [ ] Add/verify Step-level tests and golden checks.

   - tidy (tidy_tasks.py)
     - [x] Tasks already call `run_steps` with `NormalizeSpacingStep` and `EnsureSelfParamStep`.
     - [ ] Add tests to assert idempotency and spacing normalization for tricky cases.

   - Other small tasks
     - [ ] Scan `stages/` for other monolithic `Task.execute` implementations and add them to this checklist (example: any Task with a large transformer class that hasn't been wrapped yet).
5. Hardening
   - [x] Docs/specs for Steps.
   - [x] Observability tuning and env gating.

## PRs, branch names, and CHANGELOG checklist

Use the checklist below when opening migration PRs. Keep PRs small and focused when possible.

- [ ] Branch created using descriptive name: `feature/steps-migrate-<stage>` (examples below)
  - `feature/steps-migrate-raises`
  - `feature/steps-migrate-remove-unittest-artifacts`
  - `feature/steps-migrate-postvalidator`
  - `feature/steps-migrate-small-tasks` (batch of 2–3 low-risk tasks)
- [ ] Include unit tests for each new Step (happy path + 1-2 edge cases)
- [ ] Add at least one integration test that runs the Task via `run_steps` and asserts expected TaskResult.delta keys (import flags, module changes, etc.)
- [ ] Run `ruff --fix` and `mypy` locally and fix issues before PR
- [ ] Run `pytest` for affected tests (and ideally the full suite locally if change impacts generator/rewriter logic)
- [ ] Add a brief CHANGELOG entry describing the migration (example):
  - "Migrate <stage> Task to Step pipeline: introduce Parse/Transform/Emit Steps and execute via run_steps; preserve behavioral parity and add focused unit tests."
- [ ] Link the plan doc in PR description and reference acceptance criteria

## Notes
- Prefer lazy population of `Task.steps` in `Task.execute` to avoid import cycles during module import (pattern used in existing tasks).
- If parity is uncertain, keep a compatibility Step that delegates to the legacy transformer for that Step's behavior until tests/CI prove equivalence.
- Gate per-step event emission behind diagnostics flags to avoid noisy logs in normal runs.

---

Generated/updated on: 2025-09-20

## Risk management

- Regression risk: mitigate via golden comparisons after each phase.
- Over-fragmentation: enforce step size guidelines and code reviews.
- Event volume: gate per-step emission via env flags when diagnostics are off.

## Dependencies

- Existing test/golden infrastructure.
- No external library dependencies required.

## Rollback strategy

- Steps are additive; Tasks can revert to monolithic bodies by removing `run_steps` composition without affecting StageManager or Stage contracts.
