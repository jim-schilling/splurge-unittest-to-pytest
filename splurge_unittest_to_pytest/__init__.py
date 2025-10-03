"""splurge_unittest_to_pytest package.

This initializer is intentionally lightweight to avoid importing
submodules at package import time which can cause circular import
errors during test collection. Consumers and tests should import the
submodules directly (for example: ``from
splurge_unittest_to_pytest import main`` will import the
``splurge_unittest_to_pytest.main`` submodule on demand).

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

__version__ = "2025.0.4"
__author__ = "Jim Schilling"
__description__ = "Automated unittest to pytest migration tool"

# Public API names. Submodules are imported lazily when accessed.
__all__ = [
    "main",
    "MigrationOrchestrator",
    "PipelineContext",
    "MigrationConfig",
    "Result",
    "EventBus",
    "Step",
    "Task",
    "Job",
    "Pipeline",
    "LoggingSubscriber",
    "ResultStatus",
    "FixtureScope",
    "AssertionType",
    # Exceptions
    "MigrationError",
    "ParseError",
    "TransformationError",
    "ValidationError",
    "ConfigurationError",
    "DecisionAnalysisError",
    "AnalysisStepError",
    "PatternDetectionError",
    "ReconciliationError",
    "ContextError",
    "TransformationValidationError",
    "ParametrizeConversionError",
]


def __getattr__(name: str):
    """Lazily import submodules/attributes on demand to avoid circular imports.

    Tests and consumers often import package-level names like
    ``from splurge_unittest_to_pytest import MigrationOrchestrator``. Instead of
    importing all submodules at package import time (which can create
    import cycles), we import the specific submodule when the attribute is
    accessed.
    """
    import importlib

    mapping = {
        "main": "splurge_unittest_to_pytest.main",
        "cli": "splurge_unittest_to_pytest.cli",
        "MigrationOrchestrator": "splurge_unittest_to_pytest.migration_orchestrator",
        "PipelineContext": "splurge_unittest_to_pytest.context",
        "MigrationConfig": "splurge_unittest_to_pytest.context",
        "FixtureScope": "splurge_unittest_to_pytest.context",
        "AssertionType": "splurge_unittest_to_pytest.context",
        "EventBus": "splurge_unittest_to_pytest.events",
        "LoggingSubscriber": "splurge_unittest_to_pytest.events",
        "Result": "splurge_unittest_to_pytest.result",
        "ResultStatus": "splurge_unittest_to_pytest.result",
        "Job": "splurge_unittest_to_pytest.pipeline",
        "Pipeline": "splurge_unittest_to_pytest.pipeline",
        "Task": "splurge_unittest_to_pytest.pipeline",
        "Step": "splurge_unittest_to_pytest.pipeline",
        "CollectorJob": "splurge_unittest_to_pytest.jobs",
        "FormatterJob": "splurge_unittest_to_pytest.jobs",
        "OutputJob": "splurge_unittest_to_pytest.jobs",
        "UnittestPatternAnalyzer": "splurge_unittest_to_pytest.pattern_analyzer",
        "TestModule": "splurge_unittest_to_pytest.ir",
        "TestClass": "splurge_unittest_to_pytest.ir",
        "TestMethod": "splurge_unittest_to_pytest.ir",
        "Assertion": "splurge_unittest_to_pytest.ir",
        "Fixture": "splurge_unittest_to_pytest.ir",
        "Expression": "splurge_unittest_to_pytest.ir",
        # Exceptions
        "MigrationError": "splurge_unittest_to_pytest.exceptions",
        "ParseError": "splurge_unittest_to_pytest.exceptions",
        "TransformationError": "splurge_unittest_to_pytest.exceptions",
        "ValidationError": "splurge_unittest_to_pytest.exceptions",
        "ConfigurationError": "splurge_unittest_to_pytest.exceptions",
        "DecisionAnalysisError": "splurge_unittest_to_pytest.exceptions",
        "AnalysisStepError": "splurge_unittest_to_pytest.exceptions",
        "PatternDetectionError": "splurge_unittest_to_pytest.exceptions",
        "ReconciliationError": "splurge_unittest_to_pytest.exceptions",
        "ContextError": "splurge_unittest_to_pytest.exceptions",
        "TransformationValidationError": "splurge_unittest_to_pytest.exceptions",
        "ParametrizeConversionError": "splurge_unittest_to_pytest.exceptions",
    }

    if name not in mapping:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = importlib.import_module(mapping[name])

    # For 'main' and 'cli' we return the module itself; for other names
    # return the attribute from the module if present.
    if name in {"main", "cli"}:
        return module

    try:
        return getattr(module, name)
    except AttributeError:
        # Fall back to returning the module object if attribute not found
        return module


def __dir__():
    return sorted(list(globals().keys()) + __all__)
