# Component Prioritization for Hypothesis Testing

This document outlines the prioritization of components for implementing Hypothesis-based property tests, based on impact, complexity, and existing test coverage.

## Prioritization Criteria

1. **Impact**: How critical the component is to the library's core functionality
2. **Complexity**: Implementation effort and understanding required
3. **Test Coverage Gap**: How much current unit tests miss edge cases
4. **Usage Frequency**: How often the component is used in real scenarios

## Priority 1: High Impact, High Value (Implement First)

### 1. Assert Transformer (`assert_ast_rewrites.py`)
**Priority**: 🔥 Critical
**Impact**: Very High - Core transformation functionality
**Complexity**: Medium - Well-structured pure functions
**Test Coverage Gap**: High - Many edge cases in AST transformations
**Usage Frequency**: Very High - Every unittest assertion conversion

**Rationale**: The assert transformer handles the most common and complex transformations. Property-based testing here will catch edge cases in assertion rewriting that unit tests miss.

**Properties to Test**:
- Idempotence: `transform_X(transform_X(node)) == transform_X(node)`
- Conservative behavior: Invalid inputs return original node
- AST validity: Output is valid Python AST
- Semantic equivalence: Transformed code has same meaning

### 2. Import Transformer (`import_transformer.py`)
**Priority**: 🔥 Critical
**Impact**: High - Import management affects all converted files
**Complexity**: Low - String-based transformations
**Test Coverage Gap**: Medium - Edge cases in import detection
**Usage Frequency**: High - Every file with unittest imports

**Rationale**: Import transformations are applied to every file and must be correct. Property testing will ensure no duplicate or missing imports.

**Properties to Test**:
- Import addition without duplication
- No modification when no changes needed
- Syntax preservation
- Proper import ordering

## Priority 2: Medium Impact, Medium Value (Implement Second)

### 3. Config Validation (`config_validation.py`)
**Priority**: 🟡 Important
**Impact**: Medium - Configuration errors affect entire migrations
**Complexity**: Medium - Pydantic schema validation
**Test Coverage Gap**: Medium - Edge cases in validation rules
**Usage Frequency**: Medium - Used in CLI and programmatic usage

**Rationale**: Configuration validation ensures user inputs are correct. Property testing will find edge cases in validation logic.

**Properties to Test**:
- Schema validation rejects invalid configs
- Default application for missing fields
- Field constraints respected
- Serialization round-trip preservation

### 4. CLI Argument Handling (`cli.py`, `cli_adapters.py`)
**Priority**: 🟡 Important
**Impact**: Medium - CLI is primary user interface
**Complexity**: Medium - Argument parsing and validation
**Test Coverage Gap**: Low - Well-tested with unit tests
**Usage Frequency**: High - Main user entry point

**Rationale**: CLI argument handling needs to be robust. Property testing complements existing unit tests for edge cases.

**Properties to Test**:
- Argument validation rejects invalid inputs
- Path handling works with various formats
- Configuration building maps correctly
- Deterministic output for same inputs

## Priority 3: Lower Impact, Nice-to-Have (Implement Later)

### 5. Other Transformers
**Priority**: 🟢 Optional
**Impact**: Low-Medium - Specialized transformations
**Complexity**: Varies - Some complex (fixture), some simple (skip)
**Test Coverage Gap**: Varies - Some well-tested, others not
**Usage Frequency**: Low-Medium - Depends on unittest patterns used

**Components**:
- Subtest Transformer (`subtest_transformer.py`)
- Fixture Transformer (`fixture_transformer.py`)
- Skip Transformer (`skip_transformer.py`)
- Unittest Transformer (`unittest_transformer.py`)

### 6. Pipeline and Orchestration
**Priority**: 🟢 Optional
**Impact**: Low - Integration concerns
**Complexity**: High - Complex state management
**Test Coverage Gap**: Low - Integration tests exist
**Usage Frequency**: Medium - Core execution path

**Components**:
- Migration Orchestrator (`migration_orchestrator.py`)
- Pipeline (`pipeline.py`)
- Context Management (`context.py`)

## Implementation Plan

### Phase 1: Core Transformers (Weeks 1-2)
- Assert Transformer: 5-7 test functions
- Import Transformer: 3-4 test functions
- Total: ~10 property test functions

### Phase 2: Configuration & CLI (Weeks 3-4)
- Config Validation: 4-5 test functions
- CLI Components: 3-4 test functions
- Total: ~8 property test functions

### Phase 3: Extended Coverage (Weeks 5-6)
- Remaining transformers: 5-7 test functions
- Pipeline components: 3-4 test functions
- Total: ~10 property test functions

## Success Metrics

- **Coverage**: Each component achieves 80%+ property test coverage for public APIs
- **Bug Discovery**: Find and fix at least 3 edge case bugs per component
- **Performance**: Property tests run within 60 seconds per component
- **Maintenance**: Tests are readable and maintainable alongside unit tests

## Risk Mitigation

- **Start Small**: Begin with assert transformer (highest impact, manageable scope)
- **Incremental**: Add property tests alongside existing unit tests
- **Isolated**: Each component's property tests are independent
- **Fallback**: Can disable property tests if they become problematic

## Dependencies

- Hypothesis >=6.0.0 (already installed)
- libcst for AST manipulation strategies
- Existing test infrastructure (pytest, coverage)
- Component analysis completed (properties defined)

## Next Steps

1. Implement assert transformer property tests
2. Run tests to validate approach and find initial bugs
3. Iterate on strategies based on findings
4. Expand to import transformer
5. Continue with prioritized components