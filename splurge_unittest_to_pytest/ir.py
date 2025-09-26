#!/usr/bin/env python3
"""Intermediate Representation (IR) for unittest to pytest migration.

This module defines data structures that represent unittest code semantically,
making transformations more reliable and testable than direct CST manipulation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssertionType(Enum):
    """Types of unittest assertions that need transformation."""

    __test__ = False  # Tell pytest not to collect this as a test class

    ASSERT_EQUAL = "assertEqual"
    ASSERT_TRUE = "assertTrue"
    ASSERT_FALSE = "assertFalse"
    ASSERT_IS = "assertIs"
    ASSERT_IS_NONE = "assertIsNone"
    ASSERT_IS_NOT_NONE = "assertIsNotNone"
    ASSERT_IN = "assertIn"
    ASSERT_NOT_IN = "assertNotIn"
    ASSERT_IS_INSTANCE = "assertIsInstance"
    ASSERT_NOT_IS_INSTANCE = "assertNotIsInstance"
    ASSERT_RAISES = "assertRaises"
    ASSERT_RAISES_REGEX = "assertRaisesRegex"
    ASSERT_DICT_EQUAL = "assertDictEqual"
    ASSERT_LIST_EQUAL = "assertListEqual"
    ASSERT_SET_EQUAL = "assertSetEqual"
    ASSERT_TUPLE_EQUAL = "assertTupleEqual"
    ASSERT_COUNT_EQUAL = "assertCountEqual"
    ASSERT_MULTILINE_EQUAL = "assertMultiLineEqual"
    ASSERT_SEQUENCE_EQUAL = "assertSequenceEqual"
    ASSERT_ALMOST_EQUAL = "assertAlmostEqual"
    ASSERT_GREATER = "assertGreater"
    ASSERT_GREATER_EQUAL = "assertGreaterEqual"
    ASSERT_LESS = "assertLess"
    ASSERT_LESS_EQUAL = "assertLessEqual"
    ASSERT_REGEX = "assertRegex"
    ASSERT_NOT_REGEX = "assertNotRegex"
    ASSERT_WARNS = "assertWarns"
    ASSERT_WARNS_REGEX = "assertWarnsRegex"
    ASSERT_LOGS = "assertLogs"
    ASSERT_NO_LOGS = "assertNoLogs"


class FixtureScope(Enum):
    """Scope for pytest fixtures."""

    __test__ = False  # Tell pytest not to collect this as a test class

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    SESSION = "session"


@dataclass
class Expression:
    """Represents a generic expression in the code."""

    __test__ = False  # Tell pytest not to collect this as a test class

    type: str  # e.g., "Call", "Name", "Attribute", "Comparison", etc.
    value: str  # The actual code representation
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Assertion:
    """Represents a unittest assertion that needs to be transformed."""

    __test__ = False  # Tell pytest not to collect this as a test class

    arguments: list[Expression]
    assertion_type: AssertionType | None = None
    message: str | None = None
    original_location: dict[str, int] | None = None  # For debugging


@dataclass
class Fixture:
    """Represents a setup/teardown fixture that needs to be converted."""

    __test__ = False  # Tell pytest not to collect this as a test class

    name: str
    scope: FixtureScope
    setup_code: list[str]  # Code to run before test
    teardown_code: list[str]  # Code to run after test
    dependencies: list[str] = field(default_factory=list)  # Other fixtures this depends on
    is_autouse: bool = False


@dataclass
class TestMethod:
    """Represents a test method."""

    __test__ = False  # Tell pytest not to collect this as a test class

    name: str
    body: list[Assertion | Expression]  # Statements in the method
    decorators: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None


@dataclass
class TestClass:
    """Represents a test class (unittest.TestCase or regular class)."""

    __test__ = False  # Tell pytest not to collect this as a test class

    name: str
    base_classes: list[str]
    methods: list[TestMethod]
    class_setup: Fixture | None = None
    class_teardown: Fixture | None = None
    instance_setup: Fixture | None = None
    instance_teardown: Fixture | None = None
    is_unittest_class: bool = False
    _needs_pytest_import: bool = False

    @property
    def needs_pytest_import(self) -> bool:
        """Check if this class needs pytest import."""
        return self._needs_pytest_import

    @needs_pytest_import.setter
    def needs_pytest_import(self, value: bool) -> None:
        """Set whether this class needs pytest import."""
        self._needs_pytest_import = value


@dataclass
class ImportStatement:
    """Represents an import statement."""

    __test__ = False  # Tell pytest not to collect this as a test class

    module: str
    imported_items: list[str] = field(default_factory=list)
    alias: str | None = None
    import_type: str = "direct"  # "direct", "from", "relative"


@dataclass
class TestModule:
    """Represents a complete test module/file."""

    __test__ = False  # Tell pytest not to collect this as a test class

    name: str
    imports: list[ImportStatement]
    classes: list[TestClass]
    standalone_functions: list[TestMethod] = field(default_factory=list)
    global_setup: Fixture | None = None
    global_teardown: Fixture | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    _needs_pytest_import_override: bool = False  # Override flag for pytest import

    @property
    def needs_pytest_import(self) -> bool:
        """Check if this module needs pytest import."""
        return self._needs_pytest_import_override or any(cls.needs_pytest_import for cls in self.classes)

    @needs_pytest_import.setter
    def needs_pytest_import(self, value: bool) -> None:
        """Set whether this module needs pytest import."""
        self._needs_pytest_import_override = value

    def add_import(self, import_stmt: ImportStatement) -> None:
        """Add an import statement if it doesn't already exist."""
        existing_imports = {(imp.module, tuple(sorted(imp.imported_items)), imp.alias) for imp in self.imports}
        new_import_key = (import_stmt.module, tuple(sorted(import_stmt.imported_items)), import_stmt.alias)

        if new_import_key not in existing_imports:
            self.imports.append(import_stmt)

    def get_assertions_by_type(self, assertion_type: AssertionType) -> list[Assertion]:
        """Get all assertions of a specific type from all test methods."""
        assertions = []
        for cls in self.classes:
            for method in cls.methods:
                for item in method.body:
                    if isinstance(item, Assertion) and item.assertion_type == assertion_type:
                        assertions.append(item)
        return assertions

    def get_fixture_count(self) -> int:
        """Get total number of fixtures in this module."""
        count = 0
        for cls in self.classes:
            if cls.class_setup:
                count += 1
            if cls.class_teardown:
                count += 1
            if cls.instance_setup:
                count += 1
            if cls.instance_teardown:
                count += 1
        if self.global_setup:
            count += 1
        if self.global_teardown:
            count += 1
        return count
