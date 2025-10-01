(# Changelog)

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-09-30

### Added
- Validated dataclass-backed fixture state via new unit tests covering property proxies and per-class cleanup.

### Changed
- Updated `UnittestToPytestCstTransformer.visit_FunctionDef` to populate `FixtureCollectionState` containers directly.
- Ensured module/class fixture helpers use the shared state container while preserving legacy attribute accessors.
- Defaulted migration configuration and CST transformer to enable conservative subTest → `pytest.mark.parametrize` conversions; use `--subtest` or `--no-parametrize` to opt out.
- Removed the internal `subtest` configuration flag in favor of a single boolean `parametrize` option while keeping the CLI `--subtest` switch for compatibility.

### Testing
- `pytest tests/unit/test_unittest_transformer_structure.py`
- `pytest tests/unit/test_subtest_parametrize_flag.py tests/unit/test_subtest_parametrize_expanded.py`

## [2025.0.0] - 2024-09-27

Initial release of 2025.0.0 version.

