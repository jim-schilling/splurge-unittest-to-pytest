Title: Implementation Plan — Stages Redesign (2025-09-18)

Link to research
- See the detailed research, options, and recommendations: [docs/research/research-stages-redesign-2025-09-18.md](../research/research-stages-redesign-2025-09-18.md)

Purpose
- Publish a phased migration plan as actionable checklists to introduce standardized Stage/Task contracts, lifecycle events, observers, and test harnesses with minimal risk and no initial breaking changes.

Scope
- Applies to the staged pipeline under `splurge_unittest_to_pytest/stages/` and shared types under `splurge_unittest_to_pytest/types.py`.
- Focus is on contracts, hooks/observers, and testability; performance optimizations and parallelism are out of scope for this plan.

### Milestones and checklists

Stage-0: Contracts and scaffolding (no behavior change)
- Objectives
  - Introduce formal Stage/Task contracts and delta-based context merge model; add event scaffolding.
- Checklist
  - [x] Add types in `splurge_unittest_to_pytest/types.py`:
    - [x] `ContextDelta`, `TaskResult`, `StageResult`
    - [x] `Task` and `Stage` Protocols
  - [x] Add `splurge_unittest_to_pytest/stages/events.py`:
    - [x] Minimal in-process event bus and observer interfaces
    - [x] Typed event classes: `PipelineStarted/Completed`, `StageStarted/Completed/Errored`, `TaskStarted/Completed/Skipped/Errored`
  - [x] Update `StageManager` to assemble `Resources` (logger, tracer, hooks/bus, clock) and internal `emit(...)` API
  - [x] Add `CallableStage` adapter to wrap legacy stage callables as a single-task Stage
  - [x] Ensure diagnostics remain unchanged (temporarily still direct calls)
  - [x] Unit tests for new types and `CallableStage` adapter

Stage-1: Observers and diagnostics
- Objectives
  - Move diagnostics under observers; add structured logging with minimal default footprint.
- Checklist
  - [x] Implement `DiagnosticsObserver` that writes snapshots deterministically
  - [x] Implement `LoggingObserver` using stdlib logging
  - [x] Gate observers via CLI/env flag (default minimal logging)
  - [x] Wire observers into `StageManager` lifecycle events
  - [x] Unit tests: observer registration, event emission, snapshot file names/order

Stage-2: Pilot tasks in a single stage
- Objectives
  - Validate `CstTask` concept and Task harness with a contained conversion.
- Checklist
  - [x] Select pilot: `import_injector`
  - [x] Introduce 2–3 `CstTask` implementations to cover the pilot behavior
  - [x] Add `TaskTestHarness` and unit tests for each `CstTask` (initial minimal tests added)
  - [x] Ensure module outputs are equivalent to pre-refactor results (golden tests)
  - [x] Emit events for each task; verify observer outputs

Stage-3: Hook system (internal bus first; optional pluggy)
- Objectives
  - Add pre/post processors and error hooks without changing stage logic.
- Checklist
  - [x] Define hook points: `before_stage/after_stage`, `before_task/after_task`, `on_error`
  - [x] Add hook adapters on top of the internal event bus
  - [ ] Optional: integrate `pluggy` with a small `hookspec` module and adapter layer
  - [x] Unit tests for hooks: ordering, error isolation, no-op overhead

Stage-4: Broader stage decomposition
- Objectives
  - Convert additional stages into composed Tasks; introduce IDs/versioning and per-stage metrics.
- Checklist
  - [x] Identify target stages with clear sub-steps (e.g., parts of `generator`, `fixtures_stage`)
  - [x] Implement `CstTask` units per sub-step; ensure single responsibility
    - generator: BuildFixtureSpecsTask, FinalizeGeneratorTask
    - fixtures_stage: BuildTopLevelTestsTask
    - assertion_rewriter: RewriteAssertionsTask
    - raises_stage: RewriteRaisesTask, NormalizeExceptionAttrTask
    - tidy: NormalizeSpacingTask, EnsureSelfParamTask
    - decorator_and_mock_fixes: ApplyDecoratorAndMockFixesTask
    - remove_unittest_artifacts: RemoveUnittestArtifactsTask
    - postvalidator: ValidateModuleTask
    - fixture_injector: InsertFixtureNodesTask
    - rewriter: RewriteTestMethodParamsTask
  - [ ] Add per-stage metadata: stable `stage_id`, `version`
    - [x] Add `STAGE_ID`/`STAGE_VERSION` constants to `generator`, `fixtures_stage`, `import_injector`
    - [x] Emit `version` in StageStarted/StageCompleted events
    - [x] Unit test presence of version in events
  - [ ] Update reporting/JSON to include per-stage metrics (duration, errors, outcomes)
  - [x] Expand unit/integration tests to cover new task boundaries

Stage-5: Cleanup and policy hardening
- Objectives
  - Finalize delta model and documentation; deprecate in-place context mutation.
- Checklist
- [x] Replace any remaining direct context mutation with merges of `ContextDelta`
- [x] Update developer docs on contracts, observers, and task guidelines
- [ ] Remove transitional code paths no longer used (post verification)
- [ ] Confirm CLI help/docs reflect observer/diagnostics flags

### Acceptance criteria
- All existing tests pass throughout the migration; new unit tests cover `Task`, `Observer`, and hook behavior.
- Structured lifecycle events are emitted deterministically with stable schemas.
- Diagnostics snapshots via `DiagnosticsObserver` match or improve on current behavior when enabled.
- Minimal overhead when observers/hooks/tracing are disabled (near no-op path).
- Pilot stage refactor produces identical AST/output (no regressions in goldens).

### Testing strategy
- Prefer pure functions for Tasks; test with `TaskTestHarness` against minimal `PipelineContext`.
- Add an in-memory `RecordingObserver` for asserting event sequences in unit tests.
- Use integration tests to validate end-to-end equivalence for pilot and subsequent refactors.

### Risks and mitigations
- Scope creep: constrain Stage-0/1 to scaffolding only; defer functional changes to later stages.
- API churn in hooks: version hook specs and keep changes additive; provide adapters.
- Performance: keep observers/hook handling disabled by default; fast-path when no observers registered.

### Rollback plan
- Each stage/milestone lands via small PRs; if issues arise, revert last stage-specific PR without impacting the scaffolding.
- `CallableStage` adapter allows falling back to legacy callable stages at any time during migration.

### Tracking and ownership
- Open a tracking issue to map these checklists to PRs and owners.
- Reference this plan and the research document in PR descriptions.


