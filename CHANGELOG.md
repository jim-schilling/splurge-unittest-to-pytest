# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2025.0.0] - 2025-09-09

### Added
- **pytest-mock integration**: Added pytest-mock to dev dependencies for better mocking support
- **Enhanced pytest configuration**: Added `pythonpath = ["."]` to pytest configuration for improved module discovery
- **Modern test fixtures**: Migrated all tests to use pytest's `tmp_path` fixture instead of `tempfile` module

### Changed
- **Mock modernization**: Replaced all `unittest.mock` usage with `pytest-mock` fixtures (`mocker` parameter)
- **Test infrastructure**: Updated test files to use modern pytest patterns and fixtures
- **Development tools**: Replaced black + isort + flake8 with unified ruff for linting and formatting
- **Dependency cleanup**: Removed black, isort, and flake8 from dev dependencies

### Fixed
- **pytest execution**: Fixed direct `pytest` command execution by adding proper Python path configuration
- **Test isolation**: Improved test isolation using pytest's built-in temporary directory fixtures
- **Mock reliability**: Enhanced mock reliability with pytest-mock's fixture-based approach

### Technical Improvements
- **Code quality**: Unified code quality tools under ruff for consistent linting and formatting
- **Test maintainability**: Modernized test patterns for better maintainability and reliability
- **Development experience**: Improved developer experience with better test tooling and configuration

### Dependencies
- **Added**: pytest-mock (>=3.10.0)
- **Removed**: black (>=23.0.0), isort (>=5.12.0), flake8 (not present but referenced)

### Development
- **Tooling**: Migrated from separate linting/formatting tools to unified ruff
- **Testing**: Enhanced test infrastructure with modern pytest patterns
- **Configuration**: Improved pytest configuration for better developer experience

## Previous Versions

No previous versions documented. This represents a major modernization and infrastructure update.