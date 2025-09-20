```markdown
Plan: Pilot migration — assertion_rewriter → Steps (2025-09-19)

Summary
-------
This is a targeted pilot to migrate the `assertion_rewriter` Task into a small set of granular Steps that use the stabilized Step contract and `run_steps` runner. The pilot aims to validate the migration pattern, preserve Task lifecycle semantics, and add focused tests to prevent regressions.

Why this Task
----------------
- `assertion_rewriter` is complex enough to exercise real transformations but self-contained enough for an incremental migration.
- It has existing unit tests to verify behavior, making parity checks straightforward.

Scope & Constraints
-------------------
- Non-goal: rewrite internal algorithms — aim for a behavioral-preserving decomposition.
- Keep the original Task interface and lifecycle events for the pilot. The Task will expose `steps: Sequence[Step]` and use `run_steps` in tests; production code will continue to call the original logic until the pilot is validated.

Step decomposition (proposed)
-----------------------------
Propose 3 Steps (each is a class implementing the Step protocol):

1. ParseAssertionsStep
   - Input: working context including module CST or parsed nodes
   - Output: delta with `assertions_parsed` (list of internal assertion representations)
   - Errors: parsing errors collected into StepResult.errors

2. TransformAssertionsStep
   - Input: `assertions_parsed` from previous step
   - Output: delta with `assertions_transformed` (CST fragments or transformations)
   - Errors: transformation-specific errors

3. EmitAssertionsStep
   - Input: `assertions_transformed`
   - Output: delta with `emitted_nodes` or updates to the module CST
   - Side effect: writes updated module nodes into working context for later stages

Risk mitigation
---------------
- Implement Steps as thin wrappers around current internal functions. The first implementation should call existing helper functions rather than reimplement logic.
- Add thorough tests for each Step before wiring them into the Task run path.

Testing plan (high level)
-------------------------
- Unit tests for each Step (happy path + StepResult.errors + raising exceptions).
- Integration test: run the Task with `run_steps` using the Steps and verify final output matches original Task output for a small selection of sample files.

Acceptance criteria
-------------------
- All existing `assertion_rewriter` tests pass.
- New Step unit tests cover error modes and transient key behavior.
- Full suite: ruff, mypy, and pytest -n 9 pass.

Rollout
-------
- Implement Steps and tests on a feature branch.
- After green CI, merge and plan the next Task migration.

``` 
