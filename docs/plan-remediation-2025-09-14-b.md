Remediation Plan: Fix pytest conversion issues found in run 'u2p run: 2025-09-14-b'

Date: 2025-09-14

Summary
-------
This plan addresses the issues reported in `docs/issues-u2p-2025-sep-14-b.md`:

1) Conversion of unittest exception assertions produced tests that use `cm.exception` after conversion to `with pytest.raises(...) as cm:`; pytest's ExceptionInfo uses `cm.value`. This causes AttributeError at runtime.

2) Some fixtures emitted by the converter reference other fixtures by name inside their bodies instead of declaring them as function parameters. This causes runtime TypeError when calling callables like `Path(temp_dir)` where `temp_dir` is a fixture object rather than a resolved value.

3) Ensure fixtures that create files return the full path (consistent with prior remediation in `issues-u2p-2025-sep-14-a.md`) and accept dependencies via parameters.

Goals and success criteria
--------------------------
- Tests that used to fail with AttributeError/TypeError should pass after generator changes.
- Generator output should use pytest idioms correctly: `with pytest.raises(...) as cm:` followed by `cm.value` or `str(cm.value)`, and fixtures must declare other fixture dependencies in their parameter lists.
- File-creating fixtures should return absolute paths (or consistent string/Path types as the project expects) and not raw basenames.
- Regression tests added to prevent reintroduction of these issues.

Assumptions
-----------
- The collector stage currently records setup/local assignments and teardown statements but may not fully record fixture dependencies (names referenced inside RHSs).
- The generator currently emits fixture bodies by converting code that refers to variables found in the class body or setUp into top-level fixtures; not all variable references are emitted as function parameters.
- The existing NamedTuple bundler and wrapper fixtures approach from the earlier fix (`issues-u2p-2025-sep-14-a.md`) is present and should be respected.

High-level plan
----------------
1) ExceptionInfo conversion fix
   - Update conversion rule that transforms unittest "assertRaises" style to pytest style so that any use sites of the captured context variable are rewritten from `.exception` to `.value`.
   - Where code uses `.exception` only to inspect the message, we can convert to `str(cm.value)`.
   - Add a regression test that converts a small unittest snippet using `self.assertRaises(SomeError) as cm` and then checks usage of `cm.exception` in assertions; assert that generated pytest uses `cm.value`.

2) Fixture dependency detection and emission
   - Update collector to record symbol references used inside fixture bodies (RHS expressions) so generator can determine which names are other fixtures vs. local temporaries.
   - Prefer explicit parameterization: when generating a fixture, if its body references names that are emitted as other fixtures, the generated fixture signature must include those names as parameters.
   - Specifically detect when code calls constructors like `Path(temp_dir)` where `temp_dir` is another fixture; add `temp_dir` to the fixture's parameter list.
   - Add tests (regression and unit) that assert generated fixtures include parameter names when necessary.

3) File-returning fixture normalization
   - When generator emits fixtures that create files under `temp_dir`, ensure they use `Path(temp_dir)` only after receiving `temp_dir` as a parameter. Ensure they return absolute paths (as str or Path consistent with project conventions).
   - Reuse/extend logic introduced in `issues-u2p-2025-sep-14-a.md` to treat bundled attributes specially (i.e., wrapper fixtures should not return bare basenames).

4) Tests, goldens, and CI
   - Add targeted unit/regression tests in `tests/unit/` showing the failing patterns and expected converted outputs.
   - Update goldens only after generator implementation is stable; prefer small diffs.
   - Run full test-suite locally (pytest) and quality gates (ruff, mypy).

Detailed tasks and file-level changes
------------------------------------
- Collector (`stages/collector.py`)
  - Enhance analysis pass to record Name/Attribute references inside assignment RHSs and fixture bodies. Create a `body_references` set per fixture/local assignment.
  - Ensure references include names used in Call/Attribute nodes (e.g., `Path(temp_dir)`) and are resolved to simple names when possible.

- Generator (`stages/generator.py`)
  - When building `FixtureSpec` for an attribute, consult collector `body_references` to determine fixture dependencies.
  - Update emitted fixture signature to include each dependency name as a parameter.
  - Avoid adding dependencies that are local variables created within the same fixture body (only include names that map to other fixtures or previously emitted fixtures).

- Bundler (`stages/generator_parts/namedtuple_bundler.py`, `bundler_invoker.py`)
  - Ensure the attribute->fixture mapping includes dependency hints (if a bundled composite fixture depends on other fixtures, its wrapper fixtures should accept parameters).
  - Bundle detection should not obscure dependencies: if two variables are created by a single Call but that Call uses `temp_dir`, the composite fixture must list `temp_dir` as a parameter.

- Fixture builders (`converter/fixture_builders.py`) and fixtures helpers (`converter/fixtures.py`)
  - Expose `create_fixture_for_attribute(name, value_expr, dependencies=set(), teardown=...)` that emits a fixture with the correct parameter list.
  - Ensure that when `value_expr` contains calls like `Path(temp_dir)`, `dependencies` includes `temp_dir` so emitted fixture signature is `def fixture_name(temp_dir):`.

- Tests
  - Add `tests/unit/test_exceptioninfo_conversion.py` - ensure `cm.exception` -> `cm.value` conversion.
  - Add `tests/unit/test_fixture_dependency_detection.py` - converts a sample unittest that uses `temp_dir` inside a fixture body and assert emitted fixture signature includes `temp_dir`.
  - Add/extend regression test `tests/unit/test_fix_init_api_conversion.py` to include the `Path(temp_dir)` case and assert the generated `init_api_data` fixture signature includes `temp_dir`.

- Goldens
  - Add/update goldens under `tests/goldens/` after generator changes are stable.

Edge cases and considerations
---------------------------
- Name collisions: when a name is both a fixture and a local variable in the same scope, prefer treating it as fixture only if the collector determines it's provided elsewhere (e.g., as a setup assignment or another fixture). Document behavior.
- Complex expressions: dependencies inside complex expressions (e.g., `Path(temp_dir) / f"prefix_{i}.sql"`) should still detect `temp_dir` as a dependency.
- False positives: avoid adding parameters for builtins or modules (e.g., `Path` should not be considered a dependency). Collector should filter by local names and previously recorded fixture names.
- Bundled NamedTuple fixtures: preserve the composite fixture API and ensure wrapper fixtures declare the union of composite dependencies.

Acceptance criteria
-------------------
- Unit/regression tests added pass locally and prevent regressions.
- Full test-suite remains green (875 passed + any updated tests) locally.
- Lint and type-check pass (ruff/mypy).
- Goldens updated and reviewed.

Rollout steps
-------------
1) Implement collector updates and fixture builder API changes.
2) Add unit/regression tests and run them (fast loop).
3) Update generator and bundler to emit dependency-aware fixtures.
4) Run full test suite, fix failures, run ruff/mypy.
5) Regenerate goldens and commit diffs.
6) Open PR summarizing the changes and link tests and plan document.

Risks and mitigation
--------------------
- Risk: Over-eager dependency detection may add spurious parameters causing signature mismatch.
  - Mitigation: Start with conservative detection (names that appear as top-level setup assignments or other fixtures) and add more cases gradually. Add tests for false-positive scenarios.

- Risk: Large golden diffs.
  - Mitigation: Prefer targeted tests first; only update goldens after tests pass and review diffs carefully.

Follow-ups
----------
- If you want, I can implement the changes now (start with collector and fixture builder changes, add tests, and iterate). Otherwise, I can prepare a PR with the plan and suggested diffs for review.

