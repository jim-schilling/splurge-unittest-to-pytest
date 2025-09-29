## Plan: CLI / API change — `--subtest` flag

Date: 2025-09-29

Summary
-------
This proposal changes the CLI and public API surface for controlling how unittest `subTest()` blocks are converted to pytest tests. The default behavior remains converting `subTest` loops into isolated `@pytest.mark.parametrize` test invocations. A new flag, `--subtest`, will be added to opt *into* subTest-style conversion (using the pytest-subtests plugin or an equivalent mechanism). The project will not support the legacy `--parametrize` flag; new users should use `--subtest` to enable subtest-preserving behavior.

Goals
-----
- Make the default conversion behavior explicit: convert `subTest` loops to `parametrize` (isolated test invocations).
- Add `--subtest` CLI option to opt in to converting `subTest` loops into pytest tests that preserve the original `subTest` semantics (using `pytest-subtests` plugin or equivalent runtime behavior).
- Simplify code paths: places that currently check `parametrize` should check `subtest` (or `not subtest`) to choose behavior.
- Provide a clear deprecation path from `--parametrize` to `--subtest` and update API docs.

Behavior and semantics
----------------------
- Default (no flag): subtest=False → converter produces parametrized pytest test functions; each subTest becomes a separate test invocation, with a fresh function-level fixture state.
- `--subtest` provided: subtest=True → converter preserves the single-test-with-subtests semantics by generating pytest code that uses the `subtests` fixture from `pytest-subtests` (or a small compatibility shim provided by the project). This preserves in-test shared state across subtests.

CLI / API changes
-----------------
- CLI:
  - New flag: `--subtest` (boolean flag)
    - Usage: `splurge-convert --subtest ...`
    - Semantics: when present, enable conversion mode that preserves `subTest` semantics.
  - Note: the project will not support the legacy `--parametrize` flag. We intentionally avoid adding a compatibility alias to reduce maintenance burden and keep the API surface minimal before the project's initial release.

- Public API (python function call):
  - Add `subtest` boolean option: `convert(input, subtest: bool = False, ...)`.
  - Internal callers that previously relied on an explicit `parametrize` flag should be updated to `if subtest:` or `if not subtest:` accordingly.

Implementation notes
--------------------
- Add new CLI option in `cli.py` and update `pyproject`/CLI help text.
- Update any config schema, docs, and function signatures to use the new `subtest` option.
- Do not add compatibility shims for legacy flags; we will document the new flag and call out that older aliases are unsupported prior to release.

Testing and validation
----------------------
- Unit tests for CLI parsing (ensure `--subtest` is recognized and the default behavior is parametrize).
- Unit tests for converter switch: run converter in both modes against a small set of canonical files (including complex cases in `tests/data/given_and_expected_complex/51` and `53`) and verify produced artifacts match expected outputs for each mode.
- Integration test that executes generated pytest files under a local pytest run to validate runtime behavior (needs `pytest-subtests` installed to verify subtest mode).

Documentation and user messaging
--------------------------------
- Update README and CLI docs to describe the new `--subtest` flag and default behavior.
- Add a migration note describing the deprecation of `--parametrize` and showing examples for both modes.

Rollout
-------
- Stage 1 (this change): add `--subtest` flag and publish docs explaining the new behavior. No legacy aliases will be added.
- Stage 2 (after initial release): monitor user feedback and update docs/examples as required.

Open questions / assumptions
---------------------------
- Assumes maintainers prefer a default of parametrized (isolated) conversions. If the team prefers preserving exact unittest semantics as default, swap the default boolean.
- Assumes `pytest-subtests` will be the chosen runtime mechanism for reproducible `subTest` semantics. If a different strategy is desired (e.g., generate manual loops using `subtests` context manager), we will document accordingly.

Next steps
----------
1. Review and sign off on this CLI/API change plan.
2. Implement CLI and API surface changes in a small PR that wires the flag and the compatibility shim.
3. Add tests covering parsing and expected converter flows.  
