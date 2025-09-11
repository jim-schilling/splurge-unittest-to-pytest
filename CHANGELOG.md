# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

- Add `--compat` flag to control emission of autouse compatibility fixture
- Skip `__pycache__` and unreadable files during discovery to avoid Unicode/IO errors
- Ensure `import pytest` inserted before generated fixtures and respect module docstrings
 - Archive legacy `UnittestToPytestTransformer` implementation under `contrib/legacy_converter.py`;
   the staged pipeline is now the authoritative conversion engine.
 - Add an end-to-end integration test verifying converted modules are executable and
   autouse fixtures attach correctly.

## [2025.0.0] - 2025-09-09

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

## Previous Versions

No previous versions documented. This represents a major modernization and infrastructure update.