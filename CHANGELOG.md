# Changelog

## [2025.1.0] 2025-10-04

### Intelligent Configuration Assistant (Phase 3 Complete)

#### Added
- **Project Structure Analysis**:
  - `ProjectAnalyzer` class for intelligent project structure analysis
  - Automatic detection of test file patterns and method prefixes
  - Project complexity scoring and type classification (LEGACY_TESTING, MODERN_FRAMEWORK, CUSTOM_SETUP, UNKNOWN)
  - Setup method and nested class detection for complexity assessment

- **Interactive Configuration Builder**:
  - `InteractiveConfigBuilder` class for guided configuration creation
  - Project-type-specific configuration workflows (legacy, modern framework, custom setup)
  - Intelligent defaults based on project analysis
  - Interactive CLI interface with user-friendly prompts

- **Integrated Configuration Management**:
  - `IntegratedConfigurationManager` for unified configuration validation and enhancement
  - Comprehensive validation pipeline with cross-field and filesystem checks
  - Enhanced configuration results with success/failure status, warnings, and suggestions
  - Integration with existing validation, suggestion, and analysis systems

- **New CLI Command**:
  - `configure` command for interactive configuration building
  - Project analysis and intelligent configuration generation
  - YAML output option for saving configurations
  - Analysis-only mode for project inspection

#### Technical Improvements
- **Intelligent Project Analysis**: Automated detection of project characteristics and testing patterns
- **Workflow-Based Configuration**: Tailored configuration experiences based on detected project types
- **Unified Configuration Pipeline**: Integrated validation, enhancement, and suggestion system
- **Enhanced CLI Experience**: Interactive configuration building with intelligent guidance

### Advanced Error Reporting System (Phase 2 Complete)

#### Added
- **Comprehensive Error Classification System**:
  - 10 error categories (CONFIGURATION, FILESYSTEM, PARSING, TRANSFORMATION, VALIDATION, PERMISSION, DEPENDENCY, NETWORK, RESOURCE, UNKNOWN)
  - 5 severity levels (CRITICAL, HIGH, MEDIUM, LOW, INFO) with intelligent assessment
  - `SmartError` class extending `MigrationError` with rich context and suggestions

- **Context-Aware Suggestion Engine**:
  - Intelligent suggestion generation based on error type and context
  - Category-specific suggestion strategies for different error types
  - Pattern-based suggestion recognition for common error scenarios
  - Suggestion deduplication and priority-based sorting

- **Recovery Workflow Engine**:
  - 4 comprehensive recovery workflows for major error categories
  - Step-by-step guidance with validation steps and success rates
  - Interactive recovery assistant with estimated completion times
  - Context-aware workflow selection based on error characteristics

- **Interactive Error Recovery CLI**:
  - New `error-recovery` command for interactive error assistance
  - Auto-categorization of errors from error messages
  - Interactive mode with guided recovery steps
  - Non-interactive mode for automation and scripting

- **Enhanced Error Reporting Integration**:
  - `ErrorReporter` class for centralized error handling
  - Automatic error enhancement for existing exception types
  - Recovery workflow suggestions integrated into error reports
  - Comprehensive error reporting API for programmatic access

#### Technical Improvements
- **Intelligent Error Assessment**: Context-aware severity determination based on error impact
- **Pattern Recognition**: Advanced pattern matching for error classification and suggestions
- **Recovery Automation**: Structured workflows for common error resolution scenarios
- **CLI Integration**: Seamless integration with existing CLI commands and workflows
- **Enhanced Configuration Schema** with cross-field validation rules:
  - Validates incompatible option combinations (dry_run + target_root, backup_root + backup_originals)
  - File system permission validation for target_root and backup_root directories
  - Performance impact warnings for large file size limits (>50MB)
  - Enhanced degradation tier validation with better error messages

- **Intelligent Use Case Detection Engine**:
  - Pattern matching system that detects 6 distinct use cases from configuration
  - Weighted scoring algorithm for accurate use case identification
  - Extensible framework for adding new use cases and patterns

- **Smart Suggestion Engine** with context-aware recommendations:
  - 5 suggestion types (CORRECTION, ACTION, PERFORMANCE, SAFETY, OPTIMIZATION)
  - Priority-based system ensuring important suggestions are shown first
  - Use case specific optimizations tailored for different scenarios

- **Rich Field Metadata System**:
  - Complete metadata for 10+ key configuration fields with examples, constraints, and common mistakes
  - Categorized organization (input, output, backup, testing, transformation, performance, formatting, safety, error_handling)
  - Auto-generated help text for each field

- **Auto-generated Configuration Documentation**:
  - Markdown and HTML output formats with professional styling
  - Complete field reference with examples, constraints, and common mistakes
  - Categorized organization for easy navigation

- **Configuration Templates System**:
  - 6 ready-to-use templates for common scenarios (basic migration, custom framework, enterprise deployment, CI integration, development debugging, production deployment)
  - YAML and CLI argument generation for each template
  - Template suggestions based on configuration analysis
  - New CLI command `generate-templates` to create template files

- **Enhanced CLI Interface**:
  - New commands: `templates`, `template-info`, `field-help`, `generate-docs`, `generate-templates`
  - Enhanced `migrate` command with `--suggestions`, `--use-case-analysis`, `--template` flags
  - Complete CLI access to all enhanced validation features

- **Comprehensive Test Suite**:
  - 36 new tests covering all enhanced functionality
  - Cross-field validation tests (5 tests)
  - File system validation tests (3 tests)
  - Use case detection tests (6 tests)
  - Configuration suggestions tests (5 tests)
  - Field metadata tests (4 tests)
  - Documentation generation tests (3 tests)
  - Template functionality tests (6 tests)

#### Misc

- Added public helper `prepare_config` (convenience entrypoint for CLI/programmatic config preparation) and accompanying usage note in `docs/usage/prepare_config.md`.
  - Integration tests (4 tests)

- **Public helper:** Added `prepare_config` to the public API and documented its usage in `docs/usage/prepare_config.md`. This helper provides a single, consistent entrypoint to build `MigrationConfig` programmatically, applies intelligent defaults, and gracefully falls back when enhanced validation is unavailable. Added unit and integration tests to cover the helper and CLI dry-run behavior.

- **Comprehensive Configuration Documentation**: Added detailed configuration reference documentation:
  - `docs/configuration-reference.md`: Auto-generated comprehensive configuration reference
  - `docs/config-advanced-options.md`: Advanced configuration options guide
  - `docs/config-degradation-settings.md`: Degradation and fallback settings
  - `docs/config-import-handling.md`: Import handling configuration
  - `docs/config-output-settings.md`: Output and file handling settings
  - `docs/config-parametrize-settings.md`: Parametrize transformation settings
  - `docs/config-processing-options.md`: Processing and performance options
  - `docs/config-test-method-patterns.md`: Test method pattern configuration
  - `docs/config-transform-selection.md`: Transform selection options
  - `docs/config-transformation-settings.md`: General transformation settings

- **Configuration Examples and Templates**: Added practical examples and templates:
  - `examples/config-templates/`: Ready-to-use configuration templates for common scenarios
    - `basic-migration.yaml`: Basic unittest to pytest migration
    - `ci-cd-integration.yaml`: CI/CD pipeline integration
    - `comprehensive-migration.yaml`: Full-featured migration setup
    - `advanced-analysis.yaml`: Advanced analysis and reporting
    - `batch-processing.yaml`: Batch processing optimization
    - `minimal.yaml`: Minimal configuration for simple migrations
  - `examples/workflow-templates/`: Workflow templates for different migration approaches
    - `simple-migration-workflow.yaml`: Basic migration workflow
    - `comprehensive-migration-workflow.yaml`: Full migration workflow
    - `ci-cd-workflow.yaml`: CI/CD integration workflow
    - `gradual-migration-workflow.yaml`: Gradual migration approach
    - `legacy-code-workflow.yaml`: Legacy codebase migration

- **Enhanced Testing**: Added comprehensive test coverage for new features:
  - `tests/unit/test_cli_adapters_comprehensive.py`: Comprehensive CLI adapter testing
  - Additional integration tests for configuration validation and error reporting

- **Documentation Generation Tools**: Added automated documentation generation:
  - `scripts/generate_config_docs.py`: Script for generating configuration documentation
  - `splurge_unittest_to_pytest/config_docs_generator.py`: Configuration documentation generator
  - `splurge_unittest_to_pytest/config_metadata.py`: Configuration metadata system

- **Updated README Files**: Enhanced documentation with new features:
  - Updated main `README.md` with intelligent configuration features and examples
  - Updated `docs/README-DETAILS.md` with comprehensive CLI reference and usage examples
  - Added detailed explanations of configuration templates, interactive builder, and field help system

- **Simplified CLI Usage**: Added `__main__.py` module for cleaner command-line invocation:
  - Users can now run `python -m splurge_unittest_to_pytest [command]` instead of `python -m splurge_unittest_to_pytest.cli [command]`
  - Backward compatibility maintained - both invocation methods work
  - Updated all documentation examples to use the simplified command format

#### Changed
- Enhanced `ValidatedMigrationConfig` class with sophisticated cross-field validation
- Added intelligent configuration suggestions and use case detection
- Improved error messages with actionable suggestions
- Added comprehensive field metadata and documentation generation

#### Technical Improvements
- **Zero Breaking Changes** - All existing functionality preserved
- **Performance Optimized** - Sub-millisecond validation and suggestion generation
- **Extensible Architecture** - Easy to add new validation rules, use cases, and suggestions
- **Comprehensive Error Handling** - Graceful fallbacks and clear error messages
- **Type Safety** - Full type hints and validation throughout

### Previous Changes

## [2025.0.4] 2025-10-03

### Added
- Extracted caplog alias detection and AST construction into `splurge_unittest_to_pytest.transformers._caplog_helpers`.
- Added `splurge_unittest_to_pytest.transformers.debug` for `SPLURGE_TRANSFORM_DEBUG` debug gating and a `maybe_reraise` helper.
- Added unit tests:
	- `tests/unit/test_caplog_helpers_basic.py` for caplog helper behavior.
	- `tests/unit/test_debug_gate_basic.py` for debug gate behavior.
 - Added additional unit tests for path utilities:
    - `tests/unit/test_path_utils_basic.py` (basic validation and ensure_parent_dir)
    - `tests/unit/test_path_utils_edgecases.py` (empty path, invalid chars, Windows long-path, permission error simulation)
- Added parametrize decorator helper factory and tests:
	- `splurge_unittest_to_pytest.transformers.parametrize_helper._make_parametrize_call` for centralized decorator construction
	- `tests/unit/test_parametrize_decorator_helper.py` (basic decorator creation and ids kwarg handling)

### Changed
- `splurge_unittest_to_pytest.transformers.assert_transformer` now delegates caplog-related behavior to `_caplog_helpers` and re-exports thin compatibility shims to preserve public APIs.
- `splurge_unittest_to_pytest.transformers.parametrize_helper` now delegates parametrize decorator construction to a centralized `_make_parametrize_call` helper to improve testability and consistency.

### Notes
- Full test-suite run: 945 passed locally. Recommend enabling a CI job that runs the suite once with `SPLURGE_TRANSFORM_DEBUG=1` for PR verification.

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

