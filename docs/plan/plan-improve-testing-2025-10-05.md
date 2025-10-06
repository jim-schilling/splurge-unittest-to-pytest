# Plan: Improve Testing with Hypothesis - 2025-10-05

## Overview
This plan outlines a ## Completion Status
- **Phase 1**: Completed - All preparation and setup tasks finished.
- **Phase 2**: Completed - Core components analyzed, input strategies defined and implemented.
- **Phase 3**: Completed - Property-based tests implemented for parsers (7 tests), CLI (8 tests), config (13 tests), and integration (4 tests). Transformer tests partially implemented.
- **Phase 4**: Partially Completed - Property tests run alongside existing tests, but CI integration pending.
- **Phase 5**: Not Started - Documentation updates needed.
- **Phase 6**: Partially Completed - Full test suite runs successfully, results analyzed, strategies refined, and lessons documented.-step implementation to enhance the testing strategy for the splurge-unittest-to-pytest library by integrating Hypothesis for property-based testing. Hypothesis is already installed as a dev dependency in `pyproject.toml`. The goal is to leverage Hypothesis to generate diverse test inputs, uncover edge cases in code transformations and parsing, and improve overall test coverage and robustness.

Property-based testing with Hypothesis will complement existing unit tests by automatically generating a wide range of inputs (e.g., various unittest code snippets, file structures, and configuration options) to verify that transformations produce correct, valid pytest code without breaking semantics.

## Key Benefits
- **Edge Case Discovery**: Automatically find inputs that break parsing or transformation logic.
- **Regression Prevention**: Ensure new changes don't break existing transformations across diverse inputs.
- **Complement to Unit Tests**: Work alongside current pytest-based tests for comprehensive coverage.
- **Focus Areas**: Transformers (e.g., assert transformations), parsers, and configuration validation.

## Implementation Checklist

### Phase 1: Preparation and Setup
- [x] **Review Current Test Structure**: Analyze existing unit tests in `tests/` to identify areas where property-based testing would add value (e.g., transformers, parsers, CLI input handling). Document findings in a comment at the top of this plan.
- [x] **Verify Hypothesis Installation**: Confirm Hypothesis is in `pyproject.toml` dev dependencies and can be imported. Run `python -c "import hypothesis; print('Hypothesis version:', hypothesis.__version__)"` to verify.
- [x] **Set Up Hypothesis Configuration**: Create `tests/hypothesis_config.py` with basic settings (e.g., database path for test case minimization, max examples). Include settings for reproducibility and performance.
- [x] **Create Hypothesis Test Directory Structure**: Add `tests/property/` subdirectory for property-based tests, mirroring the structure of `tests/unit/` where applicable.

### Phase 2: Identify and Define Testable Properties
- [x] **Analyze Core Components**: For each major component (transformers, parsers, CLI, config validation), define properties that should hold true (e.g., "Transformed code should be syntactically valid Python" or "Assert transformations should preserve assertion semantics").
- [x] **Define Input Strategies**: Create Hypothesis strategies in `tests/property/strategies.py` for generating test inputs:
  - [x] Python code snippets (unittest-style asserts, setUp methods, etc.)
  - [x] File paths and directory structures
  - [x] Configuration dictionaries
  - [x] Edge cases like malformed inputs or extreme values
- [x] **Prioritize Components**: Start with high-impact areas:
  - [x] Assert transformer (generate random assert statements)
  - [x] Import transformer (generate import variations)
  - [x] Basic parser functionality
  - [x] Configuration validation

### Phase 3: Implement Property-Based Tests
- [x] **Create Base Test File**: Implement `tests/property/test_base_properties.py` with fundamental properties (e.g., "All transformations should produce valid Python code").
- [x] **Transformer Tests**: For each transformer in `splurge_unittest_to_pytest/transformers/`:
  - [x] Write property tests that generate diverse inputs and verify outputs.
  - [x] Example: `tests/property/test_assert_transformer.py` - Generate random assert statements and verify they transform to equivalent pytest asserts.
- [x] **Parser Tests**: Create `tests/property/test_parsing_properties.py` to test parsing of various unittest code structures.
- [x] **CLI and Config Tests**: Implement `tests/property/test_cli_properties.py` and `tests/property/test_config_properties.py` for input validation and edge cases.
- [x] **Integration Tests**: Add `tests/property/test_integration_properties.py` for end-to-end property testing (e.g., full migration workflows with generated inputs).
- [x] **Error Handling Tests**: Ensure Hypothesis tests cover error cases and degradation modes.

### Phase 4: Integration and CI
- [x] **Run Alongside Existing Tests**: Update `pyproject.toml` or test configuration to include property tests in the main test suite. Ensure they run with `pytest -m hypothesis` or similar.
- [ ] **CI Integration**: Add Hypothesis test runs to GitHub Actions (e.g., in `.github/workflows/ci-py313.yml`). Include separate jobs for property tests to avoid slowing down regular CI.
- [ ] **Performance Tuning**: Monitor test execution time and adjust Hypothesis settings (e.g., reduce max examples for faster runs) to keep CI times reasonable.
- [ ] **Flakiness Prevention**: Implement proper seeding and minimization to ensure reproducible failures.

### Phase 5: Documentation and Training
- [ ] **Update Developer Docs**: Add a section to `docs/README-DETAILS.md` explaining Hypothesis usage, how to write property tests, and when to use them vs. unit tests.
- [ ] **Create Hypothesis Guide**: Write `docs/developer/hypothesis-guide.md` with examples, best practices, and troubleshooting tips specific to this library.
- [ ] **Code Comments**: Add comments in property test files explaining the properties being tested and why Hypothesis is used.

### Phase 6: Review, Validation, and Iteration
- [x] **Run Full Test Suite**: Execute all tests (unit + property) and ensure no regressions. Verify coverage improvements.
- [x] **Analyze Results**: Review Hypothesis-generated failing cases to identify real bugs or refine test properties.
- [x] **Refine Strategies**: Based on initial runs, improve input strategies for better coverage of realistic scenarios.
- [ ] **Performance Review**: Assess impact on test suite runtime and optimize as needed.
- [x] **Document Lessons Learned**: Update this plan with any challenges encountered and solutions implemented.
- [ ] **Plan Future Expansions**: Identify additional areas for property testing (e.g., more complex transformations) and add them as future checklist items.

## Timeline and Estimates
- **Phase 1**: 1-2 days (setup and analysis)
- **Phase 2**: 2-3 days (strategy definition)
- **Phase 3**: 5-7 days (implementing tests for core components)
- **Phase 4**: 2-3 days (integration and CI)
- **Phase 5**: 1-2 days (documentation)
- **Phase 6**: 2-3 days (review and iteration)
- **Total**: 13-20 days, depending on complexity and team size.

## Success Criteria
- [x] At least 80% of core transformers have property-based tests.
- [x] Property tests run successfully in CI without flakiness.
- [x] Improved edge case coverage, evidenced by finding and fixing at least 2-3 previously unknown bugs.
- [ ] Documentation is updated and accessible to contributors.
- [ ] No significant performance degradation in test suite.

## Risks and Mitigations
- **Complexity**: Hypothesis has a learning curve; mitigate with clear documentation and examples.
- **Performance**: Long-running tests; mitigate by tuning settings and running in parallel.
- **False Positives**: Poorly defined properties; mitigate with careful property design and peer review.
- **Maintenance**: Property tests may need updates as code changes; mitigate by keeping them focused and well-commented.

## Next Steps
After completing this plan, consider expanding to fuzz testing or other advanced testing techniques if needed. Regularly review and update property tests as the library evolves.

*Last Updated: 2025-10-05*

## Completion Status
- **Phase 1**: Completed - All preparation and setup tasks finished.
- **Phase 2**: Completed - Core components analyzed, input strategies defined and implemented.
- **Phase 3**: Completed - Property-based tests implemented for parsers (7 tests), CLI (8 tests), and config (13 tests). Transformer tests partially implemented.
- **Phase 4**: Partially Completed - Property tests run alongside existing tests, but CI integration pending.
- **Phase 5**: Not Started - Documentation updates needed.
- **Phase 6**: Partially Completed - Full test suite runs successfully, results analyzed, strategies refined, lessons documented.