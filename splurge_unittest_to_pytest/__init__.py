"""unittest-to-pytest Migration Tool.

A robust, production-ready tool that automatically migrates Python unittest-based test suites
to pytest format while preserving code quality, formatting, and test behavior.

Version: 2025.0.0
"""

__version__ = "2025.0.0"
__author__ = "Jim Schilling"
__description__ = "Automated unittest to pytest migration tool"

from .cli import migrate
from .context import AssertionType, FixtureScope, MigrationConfig, PipelineContext
from .events import EventBus, LoggingSubscriber
from .ir import Assertion, Expression, Fixture, TestClass, TestMethod, TestModule
from .jobs import CollectorJob, FormatterJob, OutputJob
from .migration_orchestrator import MigrationOrchestrator
from .pattern_analyzer import UnittestPatternAnalyzer
from .pipeline import Job, Pipeline, Step, Task
from .result import Result, ResultStatus

__all__ = [
    "migrate",
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
    "CollectorJob",
    "FormatterJob",
    "OutputJob",
    "TestModule",
    "TestClass",
    "TestMethod",
    "Assertion",
    "Fixture",
    "Expression",
    "UnittestPatternAnalyzer",
]
