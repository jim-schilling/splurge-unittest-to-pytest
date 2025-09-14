Decompose and test `stages/generator` — plan

Goal

Break the large `stages/generator.py` implementation into smaller, well-documented, and unit-tested components under `stages/generator_parts/`, provide clear public contracts, and add a lightweight integration harness. The purpose is to: 

- improve testability and per-module coverage (target >=85%),
- make the generator easier to reason about and maintain,
- enable future refactors and feature work with confidence.

Principles

- Keep changes incremental and reversible: extract small components behind stable interfaces.
- Prefer pure functions or classes with minimal side-effects.
- Use the public APIs to write tests — avoid heavy internal mocks.
- Preserve the current overall external behavior of `stages/generator` (no breaking changes to pipeline) until the full test & validation pass.

High-level decomposition

The generator logic can be split into the following components (many already exist in `generator_parts/`):

1. NameAllocator
   - Responsibility: produce stable, non-colliding names for generated fixtures, temporary vars, and helper names.
   - Public API (sketch):
     - NameAllocator.allocate(base: str) -> str
     - NameAllocator.reserve(name: str) -> None
   - Tests: collisions, deterministic allocation across calls, thread-safety not required for now.

2. AnnotationInferer
   - Responsibility: decide return annotation for generated fixtures given observed expressions and heuristics.
   - Public API:
     - infer_return_annotation(func_name: str, sample_expr: Optional[cst.BaseExpression] = None) -> str | None
   - Tests: known patterns: ints -> "int", float -> "float", None -> None, collection types -> e.g. "Tuple"/"Set"/"Dict".

3. FixtureSpecBuilder
   - Responsibility: Build a small, serializable spec describing a fixture (name, return annotation, cleanup strategy, sources).
   - Public API:
     - build(name: str, body: cst.BaseStatement | str, cleanup: Optional[str]) -> FixtureSpec
   - Tests: spec correctness, JSON-serializability, equality semantics.

4. NodeEmitter
   - Responsibility: Turn a FixtureSpec and other metadata into libcst nodes (FunctionDef, decorators, body).
   - Public API (existing):
     - emit_fixture_node(name: str, body: str, returns: Optional[str] = None, decorators: Optional[dict] = None) -> cst.FunctionDef
     - emit_composite_dirs_node(base_name: str, mapping: dict[str,str]) -> cst.FunctionDef
   - Tests: many small tests asserting function shape, decorators present, code contains mapping keys, and correct return annotation when provided.

5. CleanupRewriter / Cleanup helpers
   - Responsibility: Rewrite generated fixture bodies to add cleanup and teardown logic.
   - Public API: transform(body_node: cst.FunctionDef, cleanup_spec: CleanupSpec) -> cst.FunctionDef
   - Tests: ensure cleanup instrumentation is present and works with simple bodies.

6. GeneratorCore (Orchestrator)
   - Responsibility: Coordinate the above pieces to produce final fixture nodes for a given test module.
   - Public API (existing):
     - make_fixture(name: str, body_src: str) -> cst.FunctionDef
     - make_composite_dirs_fixture(base_name: str, mapping: dict[str,str]) -> cst.FunctionDef
   - Tests: orchestrator behavior with small mocked collaborators (or use real small instances where possible) and error handling (when a subcomponent raises).

7. High-level `stages/generator.py`
   - Responsibility: Integrate GeneratorCore into the pipeline and handle file-level operations and metadata.
   - Migration approach: keep the current public behavior but gradually import refactored components from `generator_parts`.

Concrete incremental plan (safe steps)

Step A — Audit & tests for existing parts (1-2 days)
- Write or expand unit tests for existing `generator_parts` modules:
  - `node_emitter.py` — ensure all branches are covered (decorators, parameters, composite dirs).
  - `annotation_inferer.py` — add tests for type decisions.
  - `generator_core.py` — add tests for `make_fixture` and `make_composite_dirs_fixture` happy path.
- Acceptance: Tests run quickly and increase coverage for `generator_parts/*` to >=90%.

Step B — Stabilize small helpers (1 day)
- Move any ad-hoc helper functions into small modules with typed signatures and docstrings (e.g., name allocation helpers, simple formatting).
- Add small unit tests.
- Acceptance: modules pass mypy and ruff; tests added and passing.

Step C — Extract and tighten NodeEmitter API (1-2 days)
- Ensure `NodeEmitter` only takes simple inputs (FixtureSpec instead of raw strings where helpful).
- Add conversion helpers for common inputs (e.g., text->statements) with tests.
- Acceptance: NodeEmitter tests cover >95% of its lines.

Step D — Refactor GeneratorCore into an orchestrator (2-3 days)
- Keep the existing class but reduce responsibilities: delegate name allocation, spec building, and cleanup to injected collaborators.
- Introduce constructor params to allow unit tests to inject fake collaborators.
- Implement tests for orchestration: success path, subcomponent exceptions, and return-value shapes.
- Acceptance: `generator_core.py` coverage >=85%, mypy clean.

Step E — Integration harness & fixture generator smoke tests (1 day)
- Add tests that assemble real NameAllocator, SpecBuilder, NodeEmitter, and call GeneratorCore to produce 1-2 realistic fixtures (small bodies) and assert resulting libcst AST shape (function names, decorators, returns present).
- Acceptance: integration tests pass and increase `stages/generator.py` and generator_parts coverage.

Step F — Migrate `stages/generator.py` to use the new components (2-4 days)
- Small iterative changes: replace internal helper usage with new public components one at a time, run tests after each change.
- Keep compatibility layer only during the transition inside the branch (do not ship long-lived shim).
- Acceptance: complete parity tests (existing end-to-end tests) green and coverage >=85% for most modules.

Step G — Hardening and docs (1 day)
- Update docs: `docs/plan-decompose-generator.md` (this document), `CHANGELOG.md` entry, and code comments.
- Add a migration note that explains how to swap implementations and rollback steps.

Testing strategy and contracts (short)

- Contract style (per component):
  - Inputs: simple serializable types (strings, dicts, small dataclasses), libcst nodes only when necessary.
  - Outputs: libcst nodes for emitter, small dataclasses / dicts for specs, and plain dictionaries for orchestration results.
  - Errors: components raise explicit exceptions (e.g., InvalidSpecError) or return None where documented.

- Edge cases to test:
  - Empty or invalid input bodies (ensure no mutation of libcst nodes; return new nodes).
  - Unrecognized types for annotation inference.
  - Duplicate name allocation and collisions.
  - Subcomponent exceptions propagate to GeneratorCore with clear messages.

Estimate and risk

- Estimated total time: 8–14 working days (depending on interruptions and availability of reviewers). We can break that into 1–2 day tranches and run tests frequently.
- Biggest risk: `stages/generator.py` is large and has many branches; migrating without sufficient tests can introduce regressions. Mitigation: incremental steps, heavy unit tests for components, and a small regression test-suite for end-to-end behavior.

Deliverables per tranche

- Unit tests for the component(s) changed.
- Updated/created module files under `stages/generator_parts/` with types and docstrings.
- Small integration tests in `tests/unit/` that exercise public APIs.
- Updated `docs/plan-decompose-generator.md` and short CHANGELOG entry.

Follow-ups I can do right away

- Implement Step A: write the focused unit tests for `node_emitter`, `annotation_inferer`, and `generator_core` (I can add 1–3 test files as I did before). I will run them and report coverage deltas.
- Or, if you prefer, I can start with Step C and extract a small surface area of `NodeEmitter` right away.

Which next tranche would you like me to implement now? (pick one)

- "Step A: tests for existing parts" — I will add tests to raise generator_parts coverage.
- "Step C: tighten NodeEmitter" — I will change the NodeEmitter API to accept a FixtureSpec dataclass (small refactor).
- "Create migration PR" — I'll implement a branch with the changes and prepare a migration PR (requires pull-request tooling).