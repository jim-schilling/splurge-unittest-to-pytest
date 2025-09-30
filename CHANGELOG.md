(# Changelog)

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-09-30

### Added
- Validated dataclass-backed fixture state via new unit tests covering property proxies and per-class cleanup.

### Changed
- Updated `UnittestToPytestCstTransformer.visit_FunctionDef` to populate `FixtureCollectionState` containers directly.
- Ensured module/class fixture helpers use the shared state container while preserving legacy attribute accessors.

### Testing
- `pytest tests/unit/test_unittest_transformer_structure.py`

## [2025.0.0] - 2024-09-27

Initial release of 2025.0.0 version.

