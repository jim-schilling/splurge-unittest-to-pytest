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

## Rollout plan (phased)

### Phase 1 — Foundations (types, events, hooks, helper)

- Tasks
  - Add `StepId`, `StepResult`, `Step` to `types.py`.
  - Add `StepStarted/Completed/Skipped/Errored` events to `stages/events.py`.
  - Add `before_step/after_step` methods to `HookRegistry`.
  - Implement `run_steps` helper with delta folding, events, and hooks.
- Checklist
  - [ ] Compile and run unit tests.
  - [ ] Verify no lints introduced.
  - [ ] Behind env flag: optional suppression of Step events when diagnostics off.

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
  - [ ] Add unit tests for each Step (happy path + edge cases).
  - [ ] Ensure per-task events still fire; confirm additional per-step events.
  - [ ] Golden corpus: no diffs.

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
  - [ ] Step unit tests for representative inputs.
  - [ ] Task-level tests for ordering and delta folding.
  - [ ] Golden corpus: no diffs.

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
   - [ ] Implement Step types/results in `types.py`.
   - [ ] Implement Step events in `stages/events.py`.
   - [ ] Add HookRegistry methods for steps.
   - [ ] Create `run_steps` helper and tests.
2. Pilot A: import injector
   - [ ] Refactor `DetectNeedsCstTask` to Steps + tests.
   - [ ] Refactor `InsertImportsCstTask` to Steps + tests.
3. Pilot B: generator
   - [ ] Refactor `BuildFixtureSpecsTask` to Steps + tests.
   - [ ] Refactor `FinalizeGeneratorTask` (if useful) to small Steps or keep as-is.
4. Broader rollout
   - [ ] Convert fixtures and fixture injector tasks.
   - [ ] Convert rewriter tasks.
   - [ ] Convert decorator/mock fixes tasks.
   - [ ] Convert tidy tasks.
5. Hardening
   - [ ] Docs/specs for Steps.
   - [ ] Observability tuning and env gating.

## Risk management

- Regression risk: mitigate via golden comparisons after each phase.
- Over-fragmentation: enforce step size guidelines and code reviews.
- Event volume: gate per-step emission via env flags when diagnostics are off.

## Dependencies

- Existing test/golden infrastructure.
- No external library dependencies required.

## Rollback strategy

- Steps are additive; Tasks can revert to monolithic bodies by removing `run_steps` composition without affecting StageManager or Stage contracts.
