(# Changelog)

All notable changes to this project will be documented in this file.

## [2025.0.4] 2025-10-03

- Fixed version number in `__init__.py` and `pyproject.toml` to `2025.0.4`.
- Updated CLI command descriptions to reference `splurge-unittest-to-pytest` instead of `unittest-to-pytest`.
- Updated default configuration file name in `init-config` command to `splurge-unittest-to-pytest.yaml`.
- Removed stray test files from the project root directory.

## [2025.0.3] 2025-10-03

**Medium Priority Brittleness Remediation - COMPLETED**

Major robustness and reliability improvements across all core components:

### ✅ Enhanced Test Method Support (Stage 1)
- **Expanded default test prefixes**: Added support for `spec`, `should`, `it` prefixes beyond just `test`
- **Auto-detection functionality**: New `--detect-prefixes` flag automatically detects test method prefixes from source files
- **Improved configuration validation**: Enhanced error messages for test method prefix configuration

### ✅ Configuration Consolidation (Stage 2)
- **Centralized configuration management**: Improved `ValidatedMigrationConfig` class with comprehensive validation
- **Better defaults management**: Streamlined configuration handling across the application
- **Enhanced error reporting**: More informative validation messages throughout the system

### ✅ Transformation Logic Refactoring (Stage 3)
- **Function decomposition**: Broke down complex 75-line `wrap_assert_in_block` function into 4 focused helper functions
- **Improved maintainability**: Reduced complexity and improved testability of transformation logic
- **Enhanced error handling**: Better error reporting and fallback mechanisms

### ✅ Enhanced Path Handling (Stage 4)
- **Cross-platform path utilities**: Created comprehensive `path_utils.py` module
- **Windows compatibility**: Added path length validation (260 char limit) and invalid character detection
- **Enhanced error handling**: Better error messages and path-related suggestions
- **Path normalization**: Platform-aware path display utilities

### ✅ String Transformation Improvements (Stage 5)
- **Robust regex patterns**: Enhanced `_create_robust_regex()` function for whitespace tolerance
- **Comprehensive fallback**: String-level transformations with robust error handling
- **Improved regex patterns**: Made patterns tolerant of formatting variations

### ✅ Configuration Validation Optimization (Stage 6)
- **Enhanced error messages**: Improved validation messages with specific examples and guidance
- **Better user experience**: More informative error messages that help users fix configuration issues
- **Maintained safety**: Preserved comprehensive validation while improving usability

### Additional Improvements
- **Import fixes**: Corrected relative import paths for error reporting module
- **Test updates**: Updated test expectations to match improved error messages
- **Deprecated API support**: Added alias shims for deprecated unittest methods (`assertAlmostEquals`, `assertNotAlmostEquals`)
- **Cross-platform compatibility**: Enhanced Windows path handling and validation

**Impact**: Significantly reduced brittleness, improved user experience, enhanced maintainability, and better cross-platform compatibility while maintaining full backward compatibility.

## [2025.0.2] 2025-10-02

Alpha Release of splurge-unittest-to-pytest.

