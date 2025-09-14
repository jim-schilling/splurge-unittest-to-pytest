# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [2025.1.0] - 2025-09-13

### Removed
- Compatibility mode (`compat` / `--no-compat` / `--compat`) and engine selection have been removed. The converter now only supports the staged pipeline and emits strict pytest-native code.

- Removed legacy compatibility shim `splurge_unittest_to_pytest.stages.generator` — callers must use `stages.generator` directly.

### Changed
- Public API: `convert_string` and `convert_file` no longer accept `compat` or `engine` parameters. Use the staged pipeline via the public API instead.
- Tests and documentation updated to remove references to compatibility toggles and to favor the staged pipeline conversion.

### Notes
- The legacy transformer implementation and the legacy generator under `stages/generator.py` have been removed in favor of the smaller, well-tested `generator` and the staged pipeline. The converter now emits canonical per-attribute pytest fixtures by default.


## [2025.0.5] - 2025-09-13

### Added
- Strict mode (compat disabled) for pure pytest output
  - `--no-compat` drops unittest classes and lifecycle methods and emits only
    top-level pytest tests and fixtures
  - No autouse `_attach_to_instance` fixture in strict mode
  - Documented in `docs/README-DETAILS.md` with CLI and API examples
- New unit test `tests/unit/test_cli_strict_mode.py` to lock strict mode behavior

### Changed
-- CLI default and help: CLI now advertises strict/no-compat as the default output.
- Fixture injection: no-compat (strict) output now inserts two blank lines before top-level `def`/fixture blocks to produce cleaner, canonical pytest-style modules. Compat behavior preserves the previous single-empty-line spacing.

### Fixed
- CLI dry-run verbose reporting: when a file already imports `pytest`, dry-run verbose now reports "No changes needed" (avoids noisy diffs for already-converted files).
- Fixture autouse placement: ensure the autouse `_attach_to_instance` fixture (compat mode) is inserted after injected fixtures so golden comparisons and emitted code are stable.
- Added unit test `tests/unit/test_fixture_spacing.py` to assert compat vs no-compat spacing behavior.

### Changed
- Compat flag now propagates through the staged pipeline so all stages can make
  decisions deterministically
- Autouse attachment fixture is injected only when `compat=True`; no longer
  injected when `compat=False`
- Fixtures stage honors compat mode:
  - In compat mode, classes and lifecycle methods are retained for backwards
    compatibility and tests remain runnable; top-level wrappers also generated
  - In strict mode, classes/lifecycle methods are dropped and test methods are
    emitted as top-level pytest tests that accept fixtures
- CLI help text updated to clearly explain `--compat/--no-compat` semantics

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

## Previous Versions

No previous versions documented. This represents a major modernization and infrastructure update.