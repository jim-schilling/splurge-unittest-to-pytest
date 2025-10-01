#!/usr/bin/env python3
"""Intermediate Representation (IR) for unittest to pytest migration.

This module defines data structures that represent unittest code
semantically, making transformations more reliable and testable than
direct CST manipulation.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssertionType(Enum):
    """Types of unittest assertions that need transformation.

    Enum members correspond to common ``unittest.TestCase`` assertion
    helpers that are mapped to idiomatic ``pytest`` assertions.
    """

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
    """Scope values for pytest fixtures.

    Values mirror pytest's fixture scope strings: ``function``,
    ``class``, ``module``, and ``session``.
    """

    __test__ = False  # Tell pytest not to collect this as a test class

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    SESSION = "session"


@dataclass
class Expression:
    """Representation of a generic expression in source code.

    Attributes:
        type: Short string identifying the expression kind (e.g., "Call").
        value: Code-like string representation of the expression.
        metadata: Optional mapping with additional analysis data.
    """

    __test__ = False  # Tell pytest not to collect this as a test class

    type: str  # e.g., "Call", "Name", "Attribute", "Comparison", etc.
    value: str  # The actual code representation
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Assertion:
    """Represents a unittest assertion that should be transformed.

    Attributes:
        arguments: List of argument expressions for the assertion call.
        assertion_type: Optional ``AssertionType`` describing the form.
        message: Optional assertion message provided by the original call.
        original_location: Optional mapping with source location info.
    """

    __test__ = False  # Tell pytest not to collect this as a test class

    arguments: list[Expression]
    assertion_type: AssertionType | None = None
    message: str | None = None
    original_location: dict[str, int] | None = None  # For debugging


@dataclass
class Fixture:
    """Represents a setup/teardown fixture to be converted to pytest.

    Attributes:
        name: Fixture name.
        scope: ``FixtureScope`` value.
        setup_code: List of code strings to run before tests.
        teardown_code: List of code strings to run after tests.
        dependencies: Other fixtures this one depends on.
        is_autouse: Whether the fixture should be autouse.
    """

    __test__ = False  # Tell pytest not to collect this as a test class

    name: str
    scope: FixtureScope
    setup_code: list[str]  # Code to run before test
    teardown_code: list[str]  # Code to run after test
    dependencies: list[str] = field(default_factory=list)  # Other fixtures this depends on
    is_autouse: bool = False


@dataclass
class TestMethod:
    """Represents a test method.

    Attributes:
        name: Method name.
        body: Sequence of statements (Assertions or Expressions).
        decorators: Decorators applied to the method.
        parameters: Parameter names for the method.
        return_type: Optional return type annotation as a string.
    """

    __test__ = False  # Tell pytest not to collect this as a test class

    name: str
    body: list[Assertion | Expression]  # Statements in the method
    decorators: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None


@dataclass
class TestClass:
    """Represents a test class (either a ``unittest.TestCase`` or plain).

    Attributes:
        name: Class name.
        base_classes: List of base class names.
        methods: List of contained ``TestMethod`` objects.
        class_setup: Optional class-level setup ``Fixture``.
        class_teardown: Optional class-level teardown ``Fixture``.
        instance_setup: Optional instance-level setup ``Fixture``.
        instance_teardown: Optional instance-level teardown ``Fixture``.
        is_unittest_class: Whether this was originally a ``unittest.TestCase``.
    """

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
        """Return True when the class requires importing pytest.

        This property is used by generators to decide whether to add a
        top-level ``import pytest`` statement for the generated module.
        """
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
        """Return True when the module requires importing pytest.

        The module needs pytest import if any contained class requires it
        or if the override flag has been set.
        """
        return self._needs_pytest_import_override or any(cls.needs_pytest_import for cls in self.classes)

    @needs_pytest_import.setter
    def needs_pytest_import(self, value: bool) -> None:
        """Set whether this module needs pytest import."""
        self._needs_pytest_import_override = value

    def add_import(self, import_stmt: ImportStatement) -> None:
        """Add an import statement if it doesn't already exist.

        Duplicate imports (module, items, alias) are ignored.
        """
        existing_imports = {(imp.module, tuple(sorted(imp.imported_items)), imp.alias) for imp in self.imports}
        new_import_key = (import_stmt.module, tuple(sorted(import_stmt.imported_items)), import_stmt.alias)

        if new_import_key not in existing_imports:
            self.imports.append(import_stmt)

    def get_assertions_by_type(self, assertion_type: AssertionType) -> list[Assertion]:
        """Return all assertions of the specified ``AssertionType``.

        Args:
            assertion_type: The assertion type to filter by.

        Returns:
            List of matching ``Assertion`` objects.
        """
        assertions = []
        for cls in self.classes:
            for method in cls.methods:
                for item in method.body:
                    if isinstance(item, Assertion) and item.assertion_type == assertion_type:
                        assertions.append(item)
        return assertions

    def get_fixture_count(self) -> int:
        """Return the total number of fixtures in this module.

        This counts class-/instance-level fixtures and global fixtures.
        """
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
