# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2025.3.0] - 2025-09-18

### Added
- Stage tasks completed for the remaining stages:
  - `fixture_injector`: `InsertFixtureNodesTask`
  - `rewriter`: `RewriteTestMethodParamsTask`
- Developer spec documenting stage/task contracts, observers, and hooks:
  - `docs/specs/spec-stages-contracts-and-observers-2025-09-18.md`
- Observability documentation:
  - Added Observability section to `docs/README-DETAILS.md`
  - README notes on `SPLURGE_ENABLE_PIPELINE_LOGS` and diagnostics env vars

### Changed
- All stages now follow the task-based pattern with per-task lifecycle events and stable `STAGE_ID`/`STAGE_VERSION`.
- Refactored `fixture_injector` and `rewriter` stages to execute tasks and emit events.
- Tightened stage return typing to `PipelineContext` (explicit casts) to satisfy mypy.
- Cleaned transitional comments in `stages/pipeline.py` to reflect the staged pipeline as authoritative.
- CLI: improved dry-run behavior and monkeypatchable `convert_string` proxy to support tests; NDJSON/diff dry-run paths adjusted for clearer reporting.

### Fixed
- Import injector heuristics: avoid defaulting `needs_pytest_import=True` unless requested/detected; add defensive pytest/unittest usage detection; handle empty/no-import modules deterministically.
- Raises stage: propagate `needs_pytest_import` only when `pytest.raises` constructs are created; always include explicit boolean flag for test clarity.
- Generator: removed dead/legacy code and circular import by extracting `FixtureSpec` to `generator_types.py`.
- Fixture injector: restored `_find_insertion_index` shim delegating to task helper for test imports.
- Various mypy and Ruff issues across stages resolved; project is clean under both tools.

### Docs
- Plan updated (`docs/plans/plans-implement-stages-redesign-2025-09-18.md`) to mark Stage-4 items for `fixture_injector` and `rewriter`, and Stage-5 items (context-delta cleanup, developer spec) as completed.
- README updated with logging/diagnostics controls; details expanded in `docs/README-DETAILS.md`.

### Verification
- Test suite: 1096 passed, 5 skipped, 1 xfailed (on Windows, Python 3.12 local run).
- Coverage reports generated under `reports/` (HTML, XML) and JUnit XML `reports/junit.xml`.

### Version
- Bumped package version to `2025.3.0`.

## [2025.2.0] - 2025-09-17

### Removed (breaking)
- Legacy compatibility mode and all legacy compatibility flags removed. The
  converter now emits strict pytest-native code by default and no longer
  supports the historical compatibility engine. Consumers that relied on
  the legacy compatibility flag or programmatic compatibility toggles must
  update their workflows to accept strict output or implement custom adapters.

### Changed
- Project version bumped to `2025.2.0`.
- Documentation and tests updated to reflect strict-only behavior. Fixtures are
  emitted as canonical pytest fixtures and lifecycle methods (setUp/tearDown)
  are converted to top-level fixtures and test function parameters.

### Migration notes
- If you relied on compatibility mode to retain unittest-style class layouts
  (for example to preserve TestCase subclasses at runtime), update your
  workflows to accept top-level pytest test functions. To preserve class-style
  organization you can manually wrap converted functions into classes or use
  test grouping helpers in your test suite.

### Verification
- Full test-suite run: local verification performed after changes (tests and
  docs updates). Run `pytest -n 7` in your environment to confirm behavior for
  your target Python version and optional dependencies.

### Fixed
- CLI backup handling: backups are now written with a stable content-hash
  suffix (e.g., `.bak-<sha256:8>`) to avoid collisions and preserve history.
- Discovery and .gitignore handling: `find_unittest_files` now supports
  `--follow-symlinks/--no-follow-symlinks` and optionally respects `.gitignore`
  via `pathspec` when present. The discovery logic includes fallbacks for
  differing `pathspec` APIs and robust handling of unreadable files.
  Focused unit tests were added to cover both `pathspec.match_file` and
  `pathspec.match_files` variants.

### Added
- Unit tests for assertion conversion helpers: added `tests/unit/test_assertions_0001.py` to cover mapping transformations and edge cases in `splurge_unittest_to_pytest.converter.assertions`.
- Expanded test coverage (Task-5.1): added tests for `atomic_write`, import-injector alias handling, and a concurrency smoke test (skipped on Windows). These live under `tests/unit/test_io_helpers_atomic_write_0001.py`, `tests/unit/test_import_injector_alias_0001.py`, and `tests/unit/test_parallel_smoke_0001.py`.


## [2025.1.1] - 2025-09-14

### Changed
- Bumped package version and metadata to 2025.1.1.

### Fixed
- Minor packaging metadata updates and consistency fixes for release.

### Changed
- Updated generator goldens to reflect improved literal-preservation and NamedTuple bundling behavior; regenerated sample goldens from `tests/data/samples`.
 
### Notes
- Purpose: preparatory patch release that stabilizes packaging metadata and brings
  the generator goldens in line with recent conversion behavior changes.
- Verification: local formatting (`ruff`), static typing (`mypy`), and unit tests
  were run as part of validation (representative unit run: 859 passed, 1 skipped).
- Goldens: If your CI or downstream tooling performs golden-file comparisons,
  ensure the regenerated goldens under `tests/goldens/` are the intended
  baseline. Use `tools/check_generated.py` to compare sample inputs under
  `tests/data/samples` against the regenerated goldens.

### Merge guidance
- This release contains no API-breaking changes beyond previously announced
  removals (see 2025.1.0). After merging, run CI to confirm goldens and tests
  succeed in the target environment. If downstream projects pin goldens or rely
  on exact textual output, coordinate the update to accept the new goldens.

## [2025.1.0] - 2025-09-13

### Removed

- Historical: legacy compatibility shim `splurge_unittest_to_pytest.stages.generator` removed in 2025.1.0 — callers should use `stages.generator` or the staged pipeline directly.

### Changed
- Public API: `convert_string` and `convert_file` no longer accept compatibility or `engine` parameters. Use the staged pipeline via the public API instead.
- Tests and documentation updated to remove references to compatibility toggles and to favor the staged pipeline conversion.
- Test helpers: duplicate test-local autouse helper implementations were consolidated into a single test-only module (`tests/unit/helpers/autouse_helpers.py`) and removed from production code. This keeps test utilities out of the package public API.

### Repository cleanup
- Removed local generated `build/` artifacts from the working tree and ensured `build/` is ignored in `.gitignore` to avoid committing generated files.
### Verification (local)
- ruff format/check: passed (minor formatting changes)
- mypy: no type errors reported for the package
- pytest: unit tests passed locally (unit run: 859 passed, 1 skipped). Full-suite runs performed earlier reported 874 passed, 4 skipped. Coverage recorded during the run (~86% project coverage).

### Notes


## [2025.0.5] - 2025-09-13


### Changed
- CLI default and help: CLI now advertises strict output as the default.

### Fixed
- Fixture autouse placement: historical compatibility behavior inserted the autouse `_attach_to_instance` fixture after injected fixtures so golden comparisons and emitted code remained stable.
- Added unit test `tests/unit/test_fixture_spacing.py` to assert historical compatibility vs strict spacing behavior.

### Changed
- The compatibility flag previously propagated through the staged pipeline so
  stages could make decisions deterministically.
- The autouse attachment fixture was injected under legacy compatibility behavior; for strict output it is not injected.
- Historical note: fixtures stage previously honored compatibility flags; under legacy compatibility, classes and lifecycle methods were retained; under strict output, classes/lifecycle methods are dropped and test methods are emitted as top-level pytest tests that accept fixtures.
 - CLI help text was historically updated to explain compatibility flag semantics

### Fixed
- Guard self-referential placeholder fixtures (e.g., `schema_file`) to avoid
  silently broken outputs; a clear `RuntimeError` is raised with guidance
- Minor placement/spacing robustness during fixture injection under both modes

### Docs
- Extended `docs/README-DETAILS.md` with a dedicated strict mode section,
  examples, and guidance on when to use compat vs strict


## [2025.0.4] - 2025-09-12

- Diagnostics: opt-in diagnostics snapshotting and helper
  - Added `SPLURGE_ENABLE_DIAGNOSTICS` to opt in to per-run diagnostics snapshots.
  - Diagnostics are written by default under the system temporary directory. Set
    `SPLURGE_DIAGNOSTICS_ROOT` to override the root directory (useful on CI).
  - Added `SPLURGE_DIAGNOSTICS_VERBOSE` to enable more verbose diagnostics logging.
  - Added a small packaged helper `splurge-print-diagnostics` (console script) and
    module `splurge_unittest_to_pytest.print_diagnostics` to discover and print the
    most recent diagnostics marker and listing.
  - CI workflow `.github/workflows/upload-diagnostics.yml` now sets a workspace-local
    diagnostics root and uploads the diagnostics directory as an artifact. A debug
    step was added to print the diagnostics root path in job logs for easier troubleshooting.



## [2025.0.4] - 2025-09-12

- Internal: consolidate small helpers into `converter/helpers`
  - Moved small helper implementations (normalization, parsing, change-detection,
    and self-reference remover) into `splurge_unittest_to_pytest.converter.helpers`.
  - Removed the compatibility shim `splurge_unittest_to_pytest.converter.utils`.
  - This is an internal refactor only; public API surface was not intentionally
    changed for consumers of the top-level API. See the migration plan for more
    details: `docs/plan-simplification-2025-09-12.md`.
  - Stage 4 (Assertion helpers tidy): centralized assertion conversions via
    `ASSERTIONS_MAP` in `splurge_unittest_to_pytest.converter.assertions` and
    updated `converter.assertion_dispatch` to use the central map.


## [2025.0.3] - 2025-09-11

- Diagnostics: move debug snapshots out of repository
  - Diagnostic snapshots are now written to a per-run temporary directory when
    `SPLURGE_ENABLE_DIAGNOSTICS` is set. A timestamped marker file is created
    inside the diagnostics folder and contains the absolute path to the
    diagnostics directory for easy discovery.

- Mypy/type fixes and formatting improvements
  - Addressed a number of type-checking issues across the `stages/` helpers
    (formatting, import injection, fixtures stage, and manager) so `mypy` now
    reports no errors for the package. A few internal helper annotations were
    relaxed to keep libcst node handling clear and maintainable.

- Internal: formatting normalization and EmptyLine handling
  - Improved module/class-level spacing normalization to reduce formatting-only
    diffs during conversion. This reduces noisy 'has_changes' results and
    helps tests validate structural transformations instead of exact text.


## [2025.0.1] - 2025-09-11

### Changed
- Update package version to 2025.0.1
- Use dynamic package __version__ in CLI tests to avoid hard-coded version failures
- CI: run coverage job on Python 3.12 only to stabilize artifact uploads
- Docs: added coverage workflow badge and adjusted CI references for the 3.12 coverage job


### Added
- **pytest-mock integration**: Added pytest-mock to dev dependencies for better mocking support
- **Enhanced pytest configuration**: Added `pythonpath = ["."]` to pytest configuration for improved module discovery
- **Modern test fixtures**: Migrated all tests to use pytest's `tmp_path` fixture instead of `tempfile` module
- **Custom method patterns**: Added CLI options for configuring setup, teardown, and test method patterns
  - `--setup-methods`: Configure setup method patterns (comma-separated or multiple flags)
  - `--teardown-methods`: Configure teardown method patterns
  - `--test-methods`: Configure test method patterns
- **Enhanced pattern matching**: Improved method detection with camelCase/snake_case support
- **Flexible parameter handling**: Enhanced parameter removal for different method types and decorators
- **Robust whitespace handling**: Improved CLI argument parsing with comprehensive whitespace trimming

### Changed
- **Mock modernization**: Replaced all `unittest.mock` usage with `pytest-mock` fixtures (`mocker` parameter)
- **Test infrastructure**: Updated test files to use modern pytest patterns and fixtures
- **Development tools**: Replaced black + isort + flake8 with unified ruff for linting and formatting
- **Dependency cleanup**: Removed black, isort, and flake8 from dev dependencies
- **CLI interface**: Enhanced command-line interface with new pattern configuration options
- **Pattern matching**: Upgraded method detection to handle camelCase and snake_case variations

### Fixed
- **pytest execution**: Fixed direct `pytest` command execution by adding proper Python path configuration
- **Test isolation**: Improved test isolation using pytest's built-in temporary directory fixtures
- **Mock reliability**: Enhanced mock reliability with pytest-mock's fixture-based approach
- **Dead code removal**: Cleaned up unreachable code in converter methods
- **Whitespace handling**: Fixed CLI argument parsing to properly trim whitespace from pattern values

### Technical Improvements
- **Code quality**: Unified code quality tools under ruff for consistent linting and formatting
- **Test maintainability**: Modernized test patterns for better maintainability and reliability
- **Development experience**: Improved developer experience with better test tooling and configuration
- **Pattern flexibility**: Enhanced method pattern matching with case-insensitive and camelCase support
- **CLI robustness**: Improved command-line argument parsing with comprehensive edge case handling

### Dependencies
- **Added**: pytest-mock (>=3.10.0)
- **Removed**: black (>=23.0.0), isort (>=5.12.0), flake8 (not present but referenced)

### Development
- **Tooling**: Migrated from separate linting/formatting tools to unified ruff
- **Testing**: Enhanced test infrastructure with modern pytest patterns
- **Configuration**: Improved pytest configuration for better developer experience
- **CLI options**: Added comprehensive CLI options for method pattern configuration
- **Pattern API**: Exposed configurable APIs for custom method pattern detection

### Features
- **Custom method patterns**: Support for configuring setup, teardown, and test method patterns
- **Enhanced matching**: Case-insensitive pattern matching with camelCase/snake_case support
- **Flexible CLI**: Multiple ways to specify patterns (comma-separated or multiple flags)
- **Robust parsing**: Comprehensive whitespace handling and edge case management

## [2025.0.0] - 2025-09-09
- **Initial commit**
- Add `--compat` flag to control emission of autouse compatibility fixture
- Skip `__pycache__` and unreadable files during discovery to avoid Unicode/IO errors
- Ensure `import pytest` inserted before generated fixtures and respect module docstrings
 - Archive legacy transformer implementation under `contrib/legacy_converter.py`;
   the staged pipeline is now the authoritative conversion engine.
 - Add an end-to-end integration test verifying converted modules are executable and
   autouse fixtures attach correctly.

## [2025.2.0] - 2025-09-17

### Removed (breaking)
  emits strict pytest-native code by default and no longer supports the
  historical compatibility engine. Consumers that relied on `--compat` or
  programmatic compatibility toggles must update their workflows to accept
  strict output or implement custom adapters.

### Changed
  emitted as canonical pytest fixtures and lifecycle methods (setUp/tearDown)
  are converted to top-level fixtures and test function parameters.

### Tests

- Hardened golden tests: replaced brittle exact-string equality checks with an AST-aware golden comparator. The test helper parses both generated and expected code using `libcst`, strips accidental Markdown code-fence lines, and falls back to a whitespace-normalized textual compare when structural equality is not detected. This reduces flakiness due to formatting-only differences and accidental markdown artifacts in `.expected` files.

Files updated during this work:

- `tests/support/golden_compare.py` (AST-aware helper)
- `tests/data/goldens/golden_namedtuple_fixture.expected` (cleaned)
- `tests/data/goldens/sample_06_converted.expected` (canonicalized)
- Integration tests updated to use the helper: `tests/integration/test_sample06_conversion_0001.py`, `tests/integration/test_generator_imports_stages_0001.py`, `tests/integration/test_generator_goldens_0001.py`

All integration tests were run locally and verified with no remaining golden-related failures.

### Migration notes
  (for example to preserve TestCase subclasses at runtime), update your
  workflows to accept top-level pytest test functions. To preserve class-style
  organization you can manually wrap converted functions into classes or use
  test grouping helpers in your test suite.

### Verification
  docs updates). Run `pytest -n 7` in your environment to confirm behavior for
  your target Python version and optional dependencies.



No previous versions documented. This represents a major modernization and infrastructure update.