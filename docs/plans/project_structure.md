# Project Structure

```
unittest_to_pytest/
│
├── docs/                              # Documentation
│   ├── project_plan.md               # Project roadmap and milestones
│   ├── technical_specification.md    # Detailed technical architecture
│   ├── architecture_diagrams.md      # System diagrams and flows
│   ├── implementation_roadmap.md     # Phase-by-phase implementation guide
│   ├── api_reference.md             # API documentation
│   ├── user_guide.md                # End-user documentation
│   ├── troubleshooting.md           # Common issues and solutions
│   └── migration_patterns.md        # Supported transformation patterns
│
├──                               # Source code
│   └── unittest_to_pytest/
│       │
│       ├── __init__.py
│       ├── __main__.py              # Entry point for python -m unittest_to_pytest
│       │
│       ├── cli/                     # Command-line interface
│       │   ├── __init__.py
│       │   ├── main.py              # Main CLI entry point
│       │   ├── commands.py          # CLI command implementations
│       │   ├── options.py           # CLI option definitions
│       │   └── output.py            # Progress reporting and formatting
│       │
│       ├── config/                  # Configuration management
│       │   ├── __init__.py
│       │   ├── models.py            # Configuration data models
│       │   ├── loader.py            # Configuration file loading
│       │   ├── validator.py         # Configuration validation
│       │   └── defaults.py          # Default configuration values
│       │
│       ├── pipeline/                # Pipeline architecture
│       │   ├── __init__.py
│       │   ├── base.py              # Step, Task, Job base classes
│       │   ├── context.py           # PipelineContext and related
│       │   ├── result.py            # Result container and utilities
│       │   ├── orchestrator.py      # Main pipeline coordinator
│       │   └── factory.py           # Pipeline construction factory
│       │
│       ├── events/                  # Event system
│       │   ├── __init__.py
│       │   ├── bus.py               # EventBus implementation
│       │   ├── types.py             # Event type definitions
│       │   ├── subscribers.py       # Built-in event subscribers
│       │   └── decorators.py        # Event handling decorators
│       │
│       ├── ir/                      # Intermediate representation
│       │   ├── __init__.py
│       │   ├── models.py            # IR data models
│       │   ├── builder.py           # IR construction utilities
│       │   ├── validator.py         # IR validation logic
│       │   ├── serializer.py        # IR serialization for debugging
│       │   └── optimizer.py         # IR optimization passes
│       │
│       ├── analyzers/               # unittest pattern analysis
│       │   ├── __init__.py
│       │   ├── patterns.py          # Pattern detection logic
│       │   ├── unittest_analyzer.py # Main unittest analysis
│       │   ├── class_analyzer.py    # TestCase class analysis
│       │   ├── method_analyzer.py   # Test method analysis
│       │   ├── assertion_analyzer.py# Assertion pattern analysis
│       │   ├── mock_analyzer.py     # Mock usage analysis
│       │   └── dependency_analyzer.py# Dependency analysis
│       │
│       ├── transformers/            # CST transformations
│       │   ├── __init__.py
│       │   ├── base.py              # Base transformer classes
│       │   ├── unittest_to_ir.py    # unittest → IR transformation
│       │   ├── assertion_transformer.py# Assertion transformations
│       │   ├── class_transformer.py # Class structure transformations
│       │   ├── method_transformer.py# Method transformations
│       │   ├── import_transformer.py# Import statement handling
│       │   ├── mock_transformer.py  # Mock integration transformations
│       │   └── fixture_transformer.py# Fixture generation
│       │
│       ├── generators/              # Code generation
│       │   ├── __init__.py
│       │   ├── base.py              # Base generator classes
│       │   ├── pytest_generator.py  # Main pytest code generator
│       │   ├── fixture_generator.py # Fixture code generation
│       │   ├── test_generator.py    # Test function generation
│       │   ├── assertion_generator.py# Assertion code generation
│       │   ├── import_generator.py  # Import statement generation
│       │   └── formatter.py         # Code formatting utilities
│       │
│       ├── steps/                   # Concrete pipeline steps
│       │   ├── __init__.py
│       │   ├── parse_steps.py       # File parsing steps
│       │   ├── analysis_steps.py    # Pattern analysis steps
│       │   ├── transform_steps.py   # Transformation steps
│       │   ├── generation_steps.py  # Code generation steps
│       │   ├── validation_steps.py  # Validation steps
│       │   └── output_steps.py      # File output steps
│       │
│       ├── utils/                   # Utility modules
│       │   ├── __init__.py
│       │   ├── file_utils.py        # File system utilities
│       │   ├── cst_utils.py         # libcst helper functions
│       │   ├── ast_utils.py         # AST analysis utilities
│       │   ├── import_utils.py      # Import management utilities
│       │   ├── naming.py            # Name generation and validation
│       │   ├── decorators.py        # Common decorators
│       │   └── logging.py           # Logging configuration
│       │
│       ├── plugins/                 # Plugin system
│       │   ├── __init__.py
│       │   ├── base.py              # Plugin base classes
│       │   ├── manager.py           # Plugin management
│       │   ├── loader.py            # Plugin loading
│       │   └── registry.py          # Plugin registry
│       │
│       ├── reporting/               # Report generation
│       │   ├── __init__.py
│       │   ├── base.py              # Report base classes
│       │   ├── statistics.py        # Statistics collection
│       │   ├── json_reporter.py     # JSON report generation
│       │   ├── html_reporter.py     # HTML report generation
│       │   ├── markdown_reporter.py # Markdown report generation
│       │   └── text_reporter.py     # Plain text reports
│       │
│       └── exceptions.py            # Custom exception classes
│
├── tests/                           # Test suite
│   ├── unit/                        # Unit tests
│   │   ├── test_pipeline/
│   │   ├── test_analyzers/
│   │   ├── test_transformers/
│   │   ├── test_generators/
│   │   ├── test_steps/
│   │   └── test_utils/
│   │
│   ├── integration/                 # Integration tests
│   │   ├── test_end_to_end/
│   │   ├── test_pipeline_integration/
│   │   └── test_file_processing/
│   │
│   ├── fixtures/                    # Test data
│   │   ├── unittest_samples/        # Sample unittest files
│   │   ├── expected_outputs/        # Expected pytest outputs
│   │   ├── edge_cases/             # Edge case test files
│   │   └── real_world/             # Real-world test samples
│   │
│   ├── property/                    # Property-based tests
│   │   ├── test_transformation_properties.py
│   │   └── test_round_trip_properties.py
│   │
│   ├── performance/                 # Performance tests
│   │   ├── test_benchmarks.py
│   │   └── test_memory_usage.py
│   │
│   └── conftest.py                 # Pytest configuration
│
├── examples/                        # Usage examples
│   ├── basic_usage/
│   │   ├── input_unittest.py
│   │   └── output_pytest.py
│   ├── complex_scenarios/
│   │   ├── inheritance_example.py
│   │   ├── mock_example.py
│   │   └── fixture_example.py
│   └── configuration_examples/
│       ├── basic_config.yaml
│       ├── advanced_config.yaml
│       └── plugin_config.yaml
│
├── plugins/                         # Example plugins
│   ├── custom_assertion_plugin/
│   └── mock_enhancement_plugin/
│
├── scripts/                         # Development and maintenance scripts
│   ├── generate_docs.py
│   ├── run_benchmarks.py
│   ├── validate_examples.py
│   └── dogfood_migration.py        # Self-migration script
│
├── .github/                        # GitHub configuration
│   ├── workflows/
│   │   ├── ci.yml                  # Continuous integration
│   │   ├── release.yml             # Release automation
│   │   └── docs.yml                # Documentation deployment
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── pyproject.toml                  # Project configuration (Poetry/setuptools)
├── unittest-to-pytest.yaml        # Default configuration file
├── README.md                       # Project overview and usage
├── CHANGELOG.md                    # Version history
├── CONTRIBUTING.md                 # Contributing guidelines
├── LICENSE                         # License file
├── .gitignore                      # Git ignore rules
├── .pre-commit-config.yaml        # Pre-commit hooks
├── mypy.ini                        # MyPy configuration
└── pytest.ini                     # Pytest configuration
```

## Key Directories Explained

### `/src/unittest_to_pytest/`
Main source code with clear separation of concerns:
- **pipeline/**: Core pipeline architecture (Step, Task, Job)
- **ir/**: Intermediate representation data models and utilities
- **analyzers/**: Pattern detection and analysis logic
- **transformers/**: libcst-based code transformations
- **generators/**: pytest code generation from IR
- **steps/**: Concrete pipeline step implementations

### `/tests/`
Comprehensive test suite following testing pyramid:
- **unit/**: Fast, isolated tests for individual components
- **integration/**: Component interaction tests
- **property/**: Property-based testing for correctness
- **performance/**: Benchmarking and profiling tests
- **fixtures/**: Sample data and expected outputs

### `/docs/`
Complete documentation covering all aspects:
- Technical specifications and architecture
- User guides and API reference
- Implementation roadmaps and troubleshooting

### `/examples/`
Real-world usage examples and demonstrations:
- Before/after transformation examples
- Configuration file templates
- Complex scenario handling

## File Organization Principles

1. **Separation of Concerns**: Each module has a single, clear responsibility
2. **Dependency Direction**: Dependencies flow inward (utils ← transformers ← steps ← pipeline)
3. **Interface Segregation**: Small, focused interfaces rather than large ones
4. **Open/Closed Principle**: Extensible through plugins and configuration
5. **Test Organization**: Tests mirror source structure for easy navigation

## Module Dependencies

```
CLI → Pipeline → Steps → Transformers → IR
                   ↓         ↓        ↓
                Events ← Analyzers → Utils
                   ↓
              Reporting
```

This structure supports the functional pipeline architecture while maintaining clear separation of concerns and enabling easy testing, extension, and maintenance.
