## Plan: Support both `parametrize` (isolated) and `subTest` (pytest-subtests) conversions

Date: 2025-09-29

Scope
-----
This document outlines a practical plan to support converting `unittest` `subTest()` patterns into two distinct pytest patterns:

- Parametrized tests (default): each `subTest` becomes a separate `@pytest.mark.parametrize` invocation. Each case runs in isolation with fresh function-scoped fixtures.
- Subtests-preserving tests: the converter emits pytest code that uses the `subtests` fixture (from `pytest-subtests`) to preserve in-test shared state across subtests.

Objectives
----------
- Provide a reliable conversion path for complex test code containing loops with `subTest()`.
- Make it straightforward for users to choose isolation (parametrize) vs. preserving semantics (subtests) via CLI/API flags (`--subtest` as described in the separate CLI plan).
- Ensure the project ships with tests that verify both modes on a suite of real-world examples (including the moved complex examples in `tests/data/given_and_expected_complex/`).

Design principles
-----------------
- Prefer explicitness: both conversion modes should be clear in intent and visible in the generated code.
- Backwards compatibility: preserve the existing parametrize behavior as default; provide a documented opt-in for subtest-preserving conversion.
- Minimal runtime dependencies: only require `pytest-subtests` when users select `--subtest` mode; conversion should still emit runnable code but tests that rely on subtest behavior should instruct the user to install the plugin.

Implementation plan (staged)
---------------------------
Stage 1 — Discovery & smoke tests (small, low-risk)
- Collect representative complex test cases (done: files moved to `tests/data/given_and_expected_complex/` — e.g., `pytest_expected_51.txt`, `pytest_expected_53.txt`).
- Add baseline unit tests that run the current converter for both modes against these examples and assert the generated code compiles (ast.parse or import) and matches expected templates.

Stage 2 — Conversion engine: add mode switch (safe edit)
- Add top-level `subtest: bool = False` option to the main convert API and to CLI (see CLI plan).
- Inside the converter, where earlier `parametrize` checks existed, change to `if subtest:` or `if not subtest:` to select generation strategy.
- Implement two code-generation branches:
  - Parametrize branch: generate `@pytest.mark.parametrize` with stable `ids` and function-level fixtures.
  - Subtest branch: generate a single pytest test function that uses the `subtests` fixture. Example output pattern:

    def test_foo(subtests):
        repo = Repo()
        for case in cases:
            with subtests.test(msg=case['description']):
                ... assertions ...

Stage 3 — Tests and validation
- Add unit tests that compare generated code with expected outputs for both modes (place expected files alongside examples in `tests/data/given_and_expected_complex/`).
- Add integration tests that run the generated pytest files with and without `pytest-subtests`. When testing subtest mode, ensure the test runner has `pytest-subtests` installed. These tests should assert that failures and outputs align with expected behavior (for example, multiple failures in subtests are aggregated under a single test, while parametrized tests produce separate test outcomes).

Stage 4 — Documentation & examples
- Update README and docs with example conversions demonstrating the two modes and showing the difference in generated code.
- Add a migration guide with recommended choices (parametrize for isolated, fast tests; `--subtest` for exact semantic preservation when tests rely on shared in-test state).

Stage 5 — Optional: shim to emulate subTest without plugin
- If `pytest-subtests` is not acceptable as an extra dependency, provide a small compatibility shim that mimics `subtests` behavior using a context manager and custom pytest hooks. This is riskier and requires careful testing. Prefer `pytest-subtests` initially.

Edge cases & tricky conversions
------------------------------
- Nested `subTest` blocks: ensure the codegen supports nested `with subtests.test(...)` contexts or converts nested loops appropriately. Document limitations.
- Cases that capture loop variables in lambdas or closures: ensure we handle the usual late-binding pitfall when generating parametrized code (use default-arg pattern or functools.partial when necessary).
- Tests that rely on ordering or cumulative id counters: document that parametrized mode isolates and resets state; subtest mode preserves sequencing.

Acceptance criteria
-------------------
- Both conversion modes produce valid Python code (passes ast.parse and imports) for all examples in `tests/data/given_and_expected_complex/`.
- Unit tests assert that generator produces the correct mode-specific artifacts for representative inputs.
- Integration tests confirm runtime behavior: parametrize results in isolated tests; subtest mode requires `pytest-subtests` and preserves in-test shared state.

Risks and mitigations
---------------------
- Risk: Complexity of code-gen increases maintenance burden. Mitigation: keep the generation for both modes as small and well-tested branches with shared helper functions.
- Risk: Users may be confused about behavior differences. Mitigation: provide clear docs and examples and default to the more commonly-preferred isolated behavior.

Timeline estimate
-----------------
- Stage 1-2: 1–2 days
- Stage 3: 1–2 days (including setting up an integration test runner with plugin)
- Stage 4: 1 day
- Stage 5 (optional): additional 2–3 days if pursued

Next steps
----------
1. Review this plan and confirm the default preference (parametrize by default, subtest opt-in) — matches CLI plan.
2. Implement Stage 1 and Stage 2 in a small PR.  
