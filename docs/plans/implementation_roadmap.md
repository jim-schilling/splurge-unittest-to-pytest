# Implementation Roadmap

This document provides a detailed implementation guide for the unittest-to-pytest migration tool, breaking down the development into concrete, actionable tasks.

## Phase 1: Foundation (Weeks 1-3)

### Week 1: Core Infrastructure

#### Day 1-2: Project Setup
- [x] Initialize Python project with build/setuptools
- [x] Set up development environment (mypy, ruff)
- [ ] Create CI/CD pipeline (GitHub Actions)
- [x] Set up testing framework (pytest, hypothesis)
- [x] Initial project structure and module layout

#### Day 3-4: Result and Context System
```python
# Priority: HIGH - Foundation for everything
- [x] Implement Result[T] generic class with error handling
- [x] Create PipelineContext immutable data class
- [x] Add Result.map() and Result.bind() for functional composition
- [x] Unit tests for result handling edge cases
```

#### Day 5-7: Event System
```python
# Priority: HIGH - Required for observability
- [x] Implement EventBus with thread-safe publishing
- [x] Create base event types (Started, Completed, Error)
- [x] Add event subscription and handler registration
- [x] Basic logging subscriber implementation
- [ ] Event system integration tests
```

### Week 2: Pipeline Architecture

#### Day 8-9: Base Pipeline Classes
```python
# Priority: HIGH - Core abstraction
- [x] Abstract Step[T, R] base class
- [x] Task[T, R] composition class
- [x] Job[T, R] high-level orchestrator
- [x] Pipeline main coordinator class
- [x] Error propagation through pipeline layers
```

#### Day 10-11: libcst Integration Foundation
```python
# Priority: HIGH - Parse foundation
- [x] ParseSourceStep implementation with libcst
- [x] CST tree traversal utilities using libcst.matchers
- [x] Error handling for malformed Python files with libcst
- [x] CST preservation validation tests
- [x] UnittestToPytestTransformer base class with CST visitor pattern
```

#### Day 12-14: CST-Based Assertion Transformation
```python
# Priority: HIGH - Core transformation logic
- [x] CST-based assertion method transformation (visit_Call pattern matching)
- [x] libcst.matchers for systematic unittest assertion detection
- [x] AST node transformation for pytest equivalents
- [x] Comprehensive unittest assertion method support (assertEqual, assertTrue, etc.)
- [x] Collection assertion transformations (assertDictEqual, assertListEqual, etc.)
- [x] Exception assertion transformations (assertRaises, assertRaisesRegex)
- [x] Type checking assertion transformations (assertIsInstance, assertNotIsInstance)
- [ ] Warning/logging assertion transformations (assertWarns, assertLogs)
- [ ] Regex assertion transformations (assertRegex, assertNotRegex)
- [ ] **Note**: Basic assertion transformation framework implemented but integration with libcst visitor pattern needs refinement
```

### Week 3: Basic Functionality

#### Day 15-17: Core Transformation Steps
```python
# Priority: HIGH - Essential functionality
- [x] TransformAssertionsStep with common patterns
- [ ] Import management utilities
- [x] Basic TestCase class detection
- [x] Method extraction utilities
```

#### Day 18-19: Testing and Validation
```python
# Priority: HIGH - Quality assurance
- [x] Comprehensive unit tests for all steps
- [ ] Property-based tests for transformation correctness
- [x] Round-trip validation (unittest → IR → pytest → unittest)
- [x] Error handling scenario tests
```

#### Day 20-21: Phase 1 Integration
```python
# Priority: MEDIUM - Milestone completion
- [x] End-to-end pipeline integration
- [x] Basic CLI interface (argparse/typer)
- [x] Simple file processing
- [x] Phase 1 demo and documentation

## 📋 Phase 1 Status Summary

✅ **COMPLETED**: Core infrastructure (Result, Context, Events, Pipeline)
✅ **COMPLETED**: Basic unittest.TestCase transformation (inheritance removal)
✅ **COMPLETED**: Fixture transformation framework (setUp/tearDown detection)
✅ **COMPLETED**: Modular architecture with jobs/steps/transformers
✅ **COMPLETED**: Comprehensive test suite (unit and integration tests)
✅ **COMPLETED**: CLI interface and file processing
✅ **COMPLETED**: Code formatting integration (isort/black APIs)
✅ **COMPLETED**: CST/AST-based test utilities for robust validation

## 📋 Phase 2 Status Summary

✅ **COMPLETED**: Intermediate Representation (IR) data models
✅ **COMPLETED**: UnittestPatternAnalyzer for code analysis
✅ **COMPLETED**: UnittestToIRStep for CST to IR transformation
✅ **COMPLETED**: Robust test utilities with CST/AST analysis

🔄 **IN PROGRESS**: Assertion transformation (libcst visitor pattern integration)
🔄 **IN PROGRESS**: Fixture code extraction (placeholder implementation)
📅 **PLANNED**: Advanced assertion types (warnings, logging, regex)
📅 **PLANNED**: Performance optimization and packaging
```

## Phase 2: Core Transformations (Weeks 4-7)

### Week 4: Intermediate Representation

#### Day 22-24: IR Data Model
```python
# Priority: HIGH - Semantic foundation
- [x] TestModule, TestClass, TestMethod data classes
- [x] Assertion, Fixture, Expression representations
- [x] IR validation utilities
- [x] Serialization/deserialization for debugging
```

#### Day 25-26: unittest Analysis
```python
# Priority: HIGH - Pattern recognition
- [x] UnittestPatternAnalyzer implementation
- [x] TestCase inheritance detection
- [x] setUp/tearDown method identification
- [x] Assertion method cataloging
```

#### Day 27-28: IR Generation
```python
# Priority: HIGH - Critical transformation
- [x] UnittestToIRStep implementation
- [x] CST → IR transformation logic
- [x] Dependency analysis for fixtures
- [x] IR validation and error reporting
```

### Week 5: Fixture Generation

#### Day 29-31: setUp/tearDown Analysis
```python
# Priority: HIGH - Core feature
- [ ] Method dependency analysis
- [x] Scope determination logic (function/class/module)
- [x] Teardown code yield pattern generation
- [x] Fixture naming and conflict resolution
```

#### Day 32-33: Fixture Code Generation
```python
# Priority: HIGH - Core feature
- [x] Pytest fixture decorator generation
- [x] Yield vs return pattern selection
- [x] Dependency injection parameter generation
- [x] Fixture scope optimization
```

#### Day 34-35: Advanced Fixture Scenarios
```python
# Priority: MEDIUM - Edge cases
- [ ] Nested fixture dependencies
- [x] Class-level fixture sharing
- [ ] Parameterized fixture support
- [ ] Fixture cleanup error handling
- [x] unittest cleanup method transformations (addCleanup, addClassCleanup)
- [x] Context manager support (enterContext, enterClassContext)
- [x] Cleanup execution order preservation (doCleanups, doClassCleanups)
- [x] Custom cleanup function handling (addTypeEqualityFunc)
```

### Week 6: Code Generation

#### Day 36-38: Pytest Code Generator
```python
# Priority: HIGH - Output generation
- [ ] IRToPytestStep implementation
- [ ] Test function generation from IR
- [ ] Import statement optimization
- [ ] Code formatting preservation
```

#### Day 39-40: Advanced Assertions
```python
# Priority: HIGH - Comprehensive support
- [x] All unittest assertion methods mapping
- [x] Custom assertion message preservation
- [ ] Approximate equality handling (assertAlmostEqual)
- [ ] Collection assertion optimizations
```

#### Day 41-42: Class Transformation
```python
# Priority: MEDIUM - Structural changes
- [ ] TestCase class flattening to functions
- [ ] Class-level fixture extraction
- [ ] Method dependency resolution
- [ ] Import statement cleanup
```

### Week 7: Integration and Testing

#### Day 43-45: End-to-End Integration
```python
# Priority: HIGH - System integration
- [ ] Complete pipeline integration
- [ ] File I/O error handling
- [ ] Batch processing foundations
- [ ] Configuration system basics
- [x] Basic code formatting step (placeholder)
```

#### Day 46-47: Comprehensive Testing
```python
# Priority: HIGH - Quality assurance
- [ ] Real-world unittest file testing
- [ ] Edge case scenario testing
- [ ] Performance benchmarking
- [ ] Memory usage profiling
- [x] Basic formatting functionality testing
```

#### Day 48-49: Phase 2 Completion
```python
# Priority: MEDIUM - Milestone delivery
- [ ] Documentation updates
- [ ] Example transformations
- [ ] Known limitations documentation
- [ ] Phase 3 planning refinement
```

## Phase 3: Advanced Features (Weeks 8-10)

### Week 8: Mock Integration

#### Day 50-52: unittest.mock Analysis
```python
# Priority: HIGH - Common pattern
- [ ] Mock object detection and analysis
- [ ] Patch decorator transformation
- [ ] Mock assertion mapping (assert_called_with, etc.)
- [ ] Mock configuration preservation
```

#### Day 53-54: pytest-mock Integration  
```python
# Priority: HIGH - Target framework
- [ ] mocker fixture integration
- [ ] Mock creation pattern transformation
- [ ] Mock assertion transformation (mock.assert_called → mocker.call)
- [ ] Import management for pytest-mock
```

#### Day 55-56: Advanced Mock Scenarios
```python
# Priority: MEDIUM - Edge cases
- [ ] Nested mock configurations
- [ ] Mock return value chaining
- [ ] Side effect handling
- [ ] Mock reset and cleanup
```

### Week 9: Advanced Patterns

#### Day 57-59: Parameterized Tests
```python
# Priority: HIGH - Common requirement
- [ ] Subtest detection and analysis
- [ ] @pytest.mark.parametrize generation
- [ ] Parameter name and value extraction
- [ ] Test ID generation for clarity
```

#### Day 60-61: Skip and Expected Failures
```python
# Priority: MEDIUM - Test control
- [ ] @unittest.skip transformation
- [ ] @unittest.expectedFailure handling
- [ ] Conditional skip logic preservation
- [ ] Skip reason message transformation
```

#### Day 62-63: CST-Based Comprehensive Assertion Support
```python
# Priority: HIGH - Core functionality
- [ ] CST visitor patterns for all unittest assertion methods
- [ ] libcst.matchers for systematic assertion detection
- [ ] AST transformation for pytest equivalents using libcst
- [ ] Complex argument parsing with libcst (collections, regex patterns)
- [ ] Nested expression handling in assertions
- [ ] Context manager transformation (assertRaises → pytest.raises)
- [ ] Fixture-based transformation for warning/logging assertions
- [ ] Error message preservation through CST metadata
- [ ] Custom assertion method preservation and transformation
- [ ] Complex assertion logic analysis and preservation using AST analysis
- [ ] Integration testing with comprehensive assertion test suite
```

### Week 10: Complex Scenarios

#### Day 64-66: Inheritance Hierarchies
```python
# Priority: MEDIUM - Real-world complexity
- [ ] Multiple inheritance handling
- [ ] Method resolution order preservation
- [ ] Abstract test base class handling
- [ ] Mixin pattern transformation
```

#### Day 67-68: Edge Cases and Polish
```python
# Priority: MEDIUM - Robustness
- [ ] Malformed code graceful handling
- [ ] Large file processing optimization
- [ ] Memory usage optimization
- [ ] Error recovery strategies
```

#### Day 69-70: Phase 3 Integration
```python
# Priority: MEDIUM - Feature completion
- [ ] All advanced features integration
- [ ] Comprehensive testing suite
- [ ] Performance validation
- [ ] Documentation updates
```

## Phase 4: Production Ready (Weeks 11-12)

### Week 11: CLI and Configuration

#### Day 71-73: Command Line Interface
```python
# Priority: HIGH - User experience
- [ ] Typer-based CLI implementation
- [ ] File and directory processing
- [ ] Progress reporting and verbose modes
- [ ] Help documentation and examples
```

#### Day 74-75: Configuration System
```python
# Priority: HIGH - Customization
- [ ] YAML/TOML configuration file support
- [ ] Runtime configuration validation
- [ ] Default configuration generation
- [ ] Configuration override hierarchy
```

#### Day 76-77: Batch Processing
```python
# Priority: HIGH - Production use
- [ ] Parallel file processing
- [ ] Progress tracking and reporting
- [ ] Error aggregation and reporting
- [ ] Rollback and recovery options
```

### Week 12: Polish and Release

#### Day 78-80: User Experience
```python
# Priority: HIGH - Production ready
- [ ] Dry-run mode with diff preview
- [ ] Backup and restore functionality
- [ ] Migration report generation
- [ ] Clear error messages and suggestions
```

#### Day 81-82: Final Formatter Job Implementation
```python
# Priority: HIGH - Code quality and consistency
- [x] Implement FormatCodeStep with isort/black API integration
- [x] Create FormatterJob as final pipeline step
- [x] Add configuration options for line length and formatting preferences
- [x] Handle formatting failures gracefully with warnings
- [x] Integration testing of formatter job in pipeline
- [x] Performance testing for formatting operations
- [x] Set up pre-commit hooks with ruff, mypy, and pytest
```

#### Day 83-84: Performance and Packaging
```python
# Priority: MEDIUM - Quality of life
- [ ] Performance optimization passes
- [ ] Memory usage optimization
- [x] Package distribution setup
- [ ] Installation and usage documentation
- [x] Formatter dependency management (isort, black)
```

#### Day 85-86: Final Testing and Release
```python
# Priority: HIGH - Quality assurance
- [ ] End-to-end production testing with formatting
- [ ] Documentation completeness review
- [ ] Release candidate preparation
- [ ] Community feedback incorporation
- [x] Format consistency validation across test suite
```

## Implementation Guidelines

### Code Quality Standards
```python
# Every module must include:
- Type annotations for all functions
- Comprehensive docstrings (Google style)
- Unit tests with >90% coverage
- Error handling for all failure modes
- Integration tests for public APIs
```

### Testing Strategy
```python
# Test pyramid approach:
1. Unit Tests (60%) - Individual functions and classes
2. Integration Tests (30%) - Component interactions  
3. End-to-End Tests (10%) - Full pipeline scenarios
4. Property Tests - Transformation correctness validation
```

### Performance Targets
- Process 1000 test files in under 5 minutes
- Memory usage under 500MB for large codebases
- Single file transformation under 1 second
- Error recovery without pipeline failure

### Documentation Requirements
- API documentation for all public interfaces
- Architecture decision records for major choices
- User guides with real-world examples
- Migration troubleshooting guide

This roadmap provides a concrete path from initial setup to production-ready tool, with clear priorities and deliverables for each phase.
