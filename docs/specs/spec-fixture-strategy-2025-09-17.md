```markdown
Title: Fixture strategy and policy — splurge-unittest-to-pytest (2025-09-17)

Summary
-- Canonical policy: strict pytest-style output only. Legacy compatibility mode is deprecated and removed — the converter will emit idiomatic pytest code that flattens test classes into top-level test functions, converts unittest patterns to pytest-native constructs, and removes `unittest.TestCase` inheritance.

Goals
- Provide a clear, testable specification for the strict-only transformation so implementers and users know exact behaviour and acceptance criteria.
- Identify code, flags, and tests that are safe to remove now that compat mode will no longer be supported.

High-level behaviour (strict mode)
- Test structure
  - All tests in a converted file will be expressed as top-level functions named `test_*`.
  - Any `unittest.TestCase` subclasses will be removed; their test methods will be converted into top-level functions.
  - Class-level setup/teardown (`setUpClass`/`tearDownClass`) and per-test setup/teardown (`setUp`/`tearDown`) will be converted into pytest fixtures where semantically appropriate and inserted as function parameters, or converted into module-level fixtures if necessary.

- Assertions and exceptions
  - Replace `self.assert*` calls (e.g., `self.assertEqual`, `self.assertTrue`, `self.assertRaises`) with plain pytest-style `assert` statements and `with pytest.raises(...)` contexts as appropriate.

- Fixtures
  - Instance-level fixtures (created via class-level attributes, use of `self`, or `setUp`) will be converted to function-scoped pytest fixtures and injected as explicit function parameters.
  - When the original test relied on class-level state, prefer to convert to a module- or session-scoped fixture only if equivalence can be preserved safely; otherwise, preserve behavior using function-scoped fixtures and refactor code to maintain semantics.

- Mocks and decorators
  - `unittest.mock` usage remains supported; the converter should prefer to keep existing mocks unless a clean pytest-native replacement is trivially available (for example pytest markers). Decorator transformations that depend on class-scoped signatures must be rewritten to accept function-level signatures.

- Imports
  - Ensure `import pytest` is present where pytest constructs (fixtures, raises) are used. Remove `unittest` imports when no longer needed.

Edge cases and rules
- Name collisions: when moving methods to top-level functions, rename helpers or detect collisions. Prefer preserving the original qualified name by prefixing with the original class name when needed (e.g., `test_ClassName_methodname`) but only when a collision would otherwise occur.
- Preservation of test discovery: top-level functions must follow pytest discovery rules (`test_` prefix) and preserve original test ordering when practical for deterministic output.
- Side-effects: conversions must avoid introducing new side-effects (imports, module-level code) beyond what existed originally.

Acceptance criteria (for converted output)
- Golden files
  - For each existing golden that represents a previously-expected compat-mode conversion, add a new strict-mode golden demonstrating the strict-only output.
  - All strict-mode golden tests must pass in CI and be marked as canonical.

- Unit tests
  - Add unit tests for the following patterns: class → functions; setUp/tearDown → fixtures; assert conversions; raises conversions; decorator and mock rewrites.

- Behavior parity
  - For tests where runtime behavior is critical (timing, ordering, side-effects), add smoke tests that run the converted code under pytest to validate behavior equivalence where feasible.

Deprecation and removal plan (compat mode)
- Immediately (this release)
  - Document the policy change in `README.md` and `CHANGELOG.md` (breaking change). Add a migration note describing how to update tests if desired.
  - Remove any CLI flags or config options that previously toggled legacy compatibility (for example legacy compatibility flags or `--compat-mode`).

- Code removal (developer tasks)
  - Remove/clean code paths labeled `compat`, `compatibility`, or guarded by a `compat_mode` flag in the codebase (likely in `stages/rewriter_stage.py`, `stages/fixtures_stage.py`, and related pipeline wiring).
  - Remove dead helpers that supported both modes (for example, alternate signature rewrites that were only used in compat mode).
  - Update `PatternConfigurator` docs if any behaviors were used to support compat mode.

- Tests
  - Remove or update tests that specifically test compat-only behavior. If tests exercised both modes, split them and keep strict-mode assertions as canonical.

Migration notes for users
- Provide a short migration section in `README.md` showing a before/after example for a common unittest-style class converted to strict pytest functions.
- If users want to preserve class structure manually, provide a small snippet or recommend using repository-level scripts to adapt converted code (not supported by the converter itself).

Implementation checklist (developer-facing)
- [ ] Add `docs/specs/spec-fixture-strategy-2025-09-17.md` (this file).
- [ ] Update `README.md` with a breaking-change note and migration example.
- [ ] Remove CLI flags and config that enabled compat mode.
- [ ] Remove compat code paths in stage modules (make rewriter stage only produce rewrites relevant to strict mode, or remove section entirely).
- [ ] Update or delete tests that validate compat behaviour; add/update strict-mode goldens and tests.
- [ ] Run full test suite and adjust goldens until CI is green.

Security and UX considerations
- Because strict mode can be opinionated and rewrite larger quantities of code, keep `--dry-run` behaviour conservative: continue skipping files that already import `pytest` for dry-run reporting only when it's safe to assume they are already pytest-style; otherwise show diffs.

Notes
- This spec is intentionally prescriptive: the project will adopt strict pytest-style output as the only supported mode. Future work may add optional, user-driven adapters, but not as a built-in "compat" toggle.

Authors
- Jim Schilling (proposed)

``` 
