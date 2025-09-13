# Plan: Generator stage refactor — 2025-09-13

Date: 2025-09-13
Owner: automated coding agent / maintainer

Overview
--------
The current `stages/generator.py` implements a sizable amount of logic in a single module: type/annotation inference, local-name allocation, fixture-spec creation, teardown/cleanup analysis, and libcst node emission. This makes unit testing of individual behaviors difficult, causes long functions, and increases the chance of regressions when changing one concern.

Goal
----
Break the monolithic generator into small, well-tested components with clear contracts. Each component should be independently unit-testable, have a narrow responsibility, and be wired together by a small orchestrator that keeps the original `generator_stage(context)` signature.

Design principles
-----------------
- Single Responsibility: each new module provides one behavior (e.g., infer annotations).
- Pure functions where possible: prefer returning data structures over mutating shared state.
- Small public contracts: define dataclasses for inputs/outputs (e.g., FixtureSpec, AnnotationResult).
- Fast unit tests: cover each component with focused tests.
- Backwards-compatible stage API: retain `generator_stage(context)` entry point and produce the same `fixture_nodes`, `fixture_specs`, and `all_typing_needed` keys in the returned context dict.

Proposed components
-------------------
1. name_allocator.py
   - Responsibility: track module-level names and allocate deterministic unique local names for bound values.
   - API: NameAllocator(used_names: Set[str]) -> object with `choose_unique(base: str) -> str` and `reserve(name: str)`.
   - Tests: collisions, deterministic suffixing, reservation behavior.

2. annotation_inferer.py
   - Responsibility: infer best-effort libcst.Annotation nodes and list of typing names required for a given expression node.
   - API: infer_annotation(expr: Optional[cst.BaseExpression]) -> AnnotationResult where AnnotationResult has (annotation: cst.Annotation, typing_names: Set[str]).
   - Tests: scalars, lists, tuples, dicts, nested containers, fallback to Any for unknown shapes.

3. fixture_spec_builder.py
   - Responsibility: from CollectorOutput, build an intermediate FixtureSpec data structure that captures name, value expression, cleanup statements, yield_style, and whether shutil or other stdlib imports are needed.
   - API: build_fixture_specs(collector_output: CollectorOutput, name_allocator: NameAllocator) -> list[FixtureSpec]
   - Tests: single-attr setUp assignments, multi-attr grouping (if generator supports), teardown detection via `_references_attribute` logic, yield-style detection.

4. cleanup_rewriter.py
   - Responsibility: rewrite teardown/cleanup statements to refer to local bound names (if generator binds complex values to local names) and detect which stdlib modules are referenced (used_shutil, needs_shutil).
   - API: rewrite_cleanup(statements: list[cst.BaseStatement], mapping: dict[str, str]) -> tuple[list[cst.BaseStatement], Set[str]]  (rewritten statements and set of stdlib modules required)
   - Tests: check name replacement in calls like `shutil.rmtree(self.temp_dir)` -> `shutil.rmtree(_tmp_temp_dir)` and detection of shutil usage.

5. node_emitter.py
   - Responsibility: convert a FixtureSpec + AnnotationResult into a libcst.FunctionDef node (the fixture function) using the project's `converter.decorator` helpers.
   - API: emit_fixture_node(spec: FixtureSpec, ann_result: AnnotationResult) -> cst.FunctionDef
   - Tests: assert shape of emitted node, decorator form (`@pytest.fixture` vs `@pytest.fixture()`), yield vs return shapes, correct annotation present.

6. orchestrator (small)`generator_core.py`
   - Responsibility: wire components together: load module-level names, create NameAllocator, call fixture_spec_builder, call annotation_inferer per spec value, call cleanup_rewriter, call node_emitter, accumulate typing names and fixture nodes and return the context dict expected by pipeline.
   - API: generator_stage(context: dict[str, Any]) -> dict[str, Any] (keeps existing stage contract)
   - Tests: integration-style: given a small CollectorOutput and module, generator_stage produces expected fixture nodes and typing names (golden tests limited to small cases).

Data models
-----------
- FixtureSpec (existing dataclass) — keep in a central, importable module (e.g., `stages/specs.py` or keep in `stages/generator.py` but importable by tests).
- AnnotationResult = dataclass(annotation: cst.Annotation, typing_names: Set[str])

Migration & implementation steps
--------------------------------
Stage 1 — scaffolding (low risk, 1–2 hours)
- Create new modules under `splurge_unittest_to_pytest/stages/`:
  - `name_allocator.py`, `annotation_inferer.py`, `fixture_spec_builder.py`, `cleanup_rewriter.py`, `node_emitter.py`, `generator_core.py` (or similar names).
- Add minimal public functions and simple tests that assert imports/exports (sanity checks). Keep `generator_stage(context)` in place but delegate to `generator_core`.

Stage 2 — implement core behaviors (medium risk, 1–2 days)
- Port `_infer_ann` into `annotation_inferer.infer_annotation` and add tests derived from existing logic.
- Implement `NameAllocator` and port used-name snapshot logic into testable setup.
- Implement `fixture_spec_builder.build_fixture_specs` by porting collector->spec logic (no node emission yet). Add unit tests for simple cases.

Stage 3 — rewrite and emission (medium risk, 1–2 days)
- Implement `cleanup_rewriter` and `node_emitter` and wire them in `generator_core`.
- Ensure node_emitter reuses existing decorators/helpers in `converter.decorators` and `converter.simple_fixture` to keep a single canonical representation.

Stage 4 — tests & goldens (low risk, 1 day)
- Add focused unit tests for each new module.
- Add a small set of golden tests that exercise generator end-to-end for representative sample inputs (keep them minimal). Use `tests/unit/test_generator_*` naming.

Stage 5 — integration & tidy (low risk, 0.5 day)
- Run ruff/mypy/pytest; fix issues.
- Run the pipeline end-to-end in a small smoke test.

Acceptance criteria
-------------------
- Existing `generator_stage(context)` behaviour remains unchanged for the public pipeline contract: returned dict contains keys `fixture_nodes`, `fixture_specs`, `all_typing_needed`, `used_shutil` (if used before).
- Unit tests for each new module pass locally.
- Integration tests (small set) pass and CI remains green.
- New modules have type annotations and docstrings.

Edge cases and mitigations
--------------------------
- Performance: keep components efficient; avoid repeated traversals by careful data passing.
- Behavioural regressions: run golden tests and existing converter tests to catch any difference. Keep old `generator.py` logic around until the new modules are well-tested and provide bit-for-bit consistent output for existing goldens.
- Backwards compatibility: keep `generator_stage` as a thin wrapper for the new orchestrator to make migration atomic and reversible.

Testing plan
------------
- Unit tests for each component (happy path + 2–3 edge cases):
  - `tests/unit/test_name_allocator.py`
  - `tests/unit/test_annotation_inferer.py`
  - `tests/unit/test_fixture_spec_builder.py`
  - `tests/unit/test_cleanup_rewriter.py`
  - `tests/unit/test_node_emitter.py`
- Integration/golden tests: `tests/unit/test_generator_core.py` comparing output shape and node-structure for 3 representative small samples.

Deliverables
------------
- New files under `splurge_unittest_to_pytest/stages/` containing the components above.
- Unit tests under `tests/unit/` for each component.
- A brief README or docstring at `docs/plan-generator-refactor-2025-09-13.md` describing the plan (this file).
- Keep the original `generator.py` in place as a fallback during migration; once the new components are validated, replace or remove it in a follow-up change.

Timeline & prioritization
-------------------------
- Phase 1 (scaffold + tests): 0.5 — 1 day
- Phase 2 (annotation & allocator): 0.5 — 1 day
- Phase 3 (spec builder, cleanup, emitter): 1 — 2 days
- Phase 4 (tests, goldens, CI): 0.5 — 1 day

Notes
-----
- Prefer incremental, test-driven migration: add components and tests first, then wire each behavior into `generator_stage` gradually.
- Keep naming and API small and explicit: a future refactor should make `annotation_inferer` reusable by other stages.

---

Document created 2025-09-13.
