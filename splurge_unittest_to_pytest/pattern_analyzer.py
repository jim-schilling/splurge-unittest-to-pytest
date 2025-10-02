#!/usr/bin/env python3
"""Pattern analyzer for unittest code.

This module analyzes ``unittest`` code patterns and identifies structures
that should be transformed into pytest equivalents. The analyzer builds a
lightweight IR (``TestModule``, ``TestClass``, ``TestMethod``, etc.) that
downstream generators consume.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import libcst as cst

from .ir import (
    Assertion,
    AssertionType,
    Expression,
    Fixture,
    FixtureScope,
    TestClass,
    TestMethod,
    TestModule,
)


class UnittestPatternAnalyzer(cst.CSTVisitor):
    """Visitor that identifies unittest patterns and produces IR.

    The visitor collects classes, methods, fixtures, and assertions and
    exposes the parsed ``TestModule`` via ``analyze_module``.
    """

    def __init__(self, test_prefixes: list[str] | None = None) -> None:
        self.needs_pytest_import = False
        self.current_class: TestClass | None = None
        self.current_method: TestMethod | None = None
        self.ir_module: TestModule | None = None
        self._class_bases: dict[str, list[str]] = {}
        self._classes: dict[str, TestClass] = {}
        self.test_prefixes = test_prefixes or ["test"]
        # Track class hierarchy for nested test classes
        self._class_stack: list[TestClass] = []

    def _normalize_base_name(self, value: cst.BaseExpression) -> str:
        """Normalize a base expression to a dotted name string if possible.

        Args:
            value: A CST base expression node.

        Returns:
            Dotted string representation when possible, otherwise a best-effort
            string fallback.
        """
        if isinstance(value, cst.Name):
            return value.value
        if isinstance(value, cst.Attribute):
            left = self._normalize_base_name(value.value)
            right = value.attr.value
            return f"{left}.{right}" if left else right
        # Fallback string
        try:
            return cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=value)])]).code.strip()
        except Exception:
            return str(value)

    def analyze_module(self, code: str) -> TestModule:
        """Analyze a Python module and return its IR representation.

        Args:
            code: The Python source code to analyze.

        Returns:
            ``TestModule`` representing the discovered tests, fixtures, and
            imports.
        """
        try:
            # Parse the code into CST
            module = cst.parse_module(code)

            # Create the IR module
            ir_module = TestModule(
                name="test_module",  # Will be updated with actual filename
                imports=[],
                classes=[],
                standalone_functions=[],
                global_setup=None,
                global_teardown=None,
                metadata={},
                _needs_pytest_import_override=False,
            )

            # Store reference for visitor methods
            self.ir_module = ir_module

            # Analyze the module
            module.visit(self)

            # Propagate unittest inheritance
            changed = True
            while changed:
                changed = False
                for cls_name, bases in self._class_bases.items():
                    cls = self._classes.get(cls_name)
                    if not cls or cls.is_unittest_class:
                        continue
                    for base_name in bases:
                        base_cls = self._classes.get(base_name)
                        if base_cls and base_cls.is_unittest_class:
                            cls.is_unittest_class = True
                            changed = True
                            break

            # Attach collected classes to module
            ir_module.classes.extend(self._classes.values())

            # Update module with collected information
            ir_module.needs_pytest_import = any(c.is_unittest_class for c in self._classes.values())

            return ir_module

        except Exception as e:
            raise ValueError(f"Failed to analyze module: {e}") from e

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Handle a class definition and record test-class information.

        This method records base classes, detects ``unittest.TestCase``
        inheritance, and collects methods for later processing. Also handles
        nested test classes by maintaining a class hierarchy stack.
        """
        class_name = node.name.value

        # Check if this is a unittest.TestCase
        is_unittest_class = self._is_unittest_testcase(node)

        # Normalize base names
        bases_norm = [self._normalize_base_name(base.value) for base in node.bases]

        # Create IR class with enhanced metadata
        test_class = TestClass(
            name=class_name,
            base_classes=bases_norm,
            methods=[],
            is_unittest_class=is_unittest_class,
        )

        # Track bases and class
        self._class_bases[class_name] = bases_norm
        self._classes[class_name] = test_class

        # Handle nested classes by pushing to stack
        self._class_stack.append(test_class)

        # Store current class for method analysis
        old_class = self.current_class
        self.current_class = test_class

        # Visit all class body items
        for item in node.body.body:
            item.visit(self)

        # Metadata about custom setup methods is tracked in the visit_FunctionDef method

        # Restore previous class and pop from stack
        self.current_class = old_class
        self._class_stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Handle a function definition to classify test methods and fixtures.

        Module-level functions are treated as standalone functions and
        converted to ``TestMethod`` entries in the IR when appropriate.
        """
        func_name = node.name.value

        # Check if this is a setUp/tearDown method
        if self._is_setup_method(func_name):
            self._analyze_setup_method(node, func_name)
            return
        elif self._is_teardown_method(func_name):
            self._analyze_teardown_method(node, func_name)
            return

        # Check if this is a test method
        if self._is_test_method(func_name):
            self._analyze_test_method(node, func_name)
            return

        # Regular function - add to standalone functions if in module level
        if self.current_class is None:
            # This is a module-level function
            return_type = None
            if node.returns and node.returns.annotation:
                return_type = self._normalize_base_name(node.returns.annotation)

            standalone_function = TestMethod(
                name=func_name,
                decorators=[],
                body=[],
                parameters=[param.name.value for param in node.params.params] if node.params else [],
                return_type=return_type,
            )

            if self.ir_module is not None:
                self.ir_module.standalone_functions.append(standalone_function)

    def visit_Call(self, node: cst.Call) -> None:
        """Inspect call expressions to detect unittest assertion calls.

        When an assertion call (e.g., ``self.assertEqual``) is found the
        analyzer records an ``Assertion`` object in the current method IR.
        """
        if isinstance(node.func, cst.Attribute):
            if isinstance(node.func.value, cst.Name) and node.func.value.value == "self":
                method_name = node.func.attr.value

                # Check if this is a unittest assertion
                assertion_type = self._get_assertion_type(method_name)
                if assertion_type:
                    self._analyze_assertion(node, assertion_type)

    def _is_unittest_testcase(self, node: cst.ClassDef) -> bool:
        """Return True when a class inherits from ``unittest.TestCase``.

        The check handles both fully-qualified base names and imported
        ``TestCase`` symbols.
        """
        for base in node.bases:
            value = base.value
            # unittest.TestCase
            if isinstance(value, cst.Attribute):
                if (
                    isinstance(value.value, cst.Name)
                    and value.value.value == "unittest"
                    and value.attr.value == "TestCase"
                ):
                    return True
            # bare TestCase (from import unittest import TestCase)
            if isinstance(value, cst.Name) and value.value == "TestCase":
                return True
        return False

    def _is_test_method(self, method_name: str) -> bool:
        """Return True when the method name follows pytest/unittest test naming.

        Uses configurable test prefixes to support various naming conventions
        like 'test_', 'spec_', 'should_', 'it_', etc.
        """
        return any(method_name.startswith(prefix) for prefix in self.test_prefixes)

    def _is_setup_method(self, method_name: str) -> bool:
        """Check if a method is a setup method."""
        # Standard unittest setup methods
        standard_setup = method_name in ["setUp", "setUpClass"]
        if standard_setup:
            return True

        # Custom setup method patterns
        setup_patterns = [
            "setup",
            "set_up",
            "setup_method",
            "setup_class",
            "before",
            "before_each",
            "before_all",
            "initialize",
            "init_test",
            "prepare",
        ]

        return any(method_name.lower().startswith(pattern) for pattern in setup_patterns)

    def _is_teardown_method(self, method_name: str) -> bool:
        """Check if a method is a teardown method."""
        # Standard unittest teardown methods
        standard_teardown = method_name in ["tearDown", "tearDownClass"]
        if standard_teardown:
            return True

        # Custom teardown method patterns
        teardown_patterns = [
            "teardown",
            "tear_down",
            "teardown_method",
            "teardown_class",
            "cleanup",
            "clean_up",
            "after",
            "after_each",
            "after_all",
            "destroy",
            "finalize",
        ]

        return any(method_name.lower().startswith(pattern) for pattern in teardown_patterns)

    def _get_assertion_type(self, method_name: str) -> AssertionType | None:
        """Convert unittest assertion method name to ``AssertionType``.

        Returns the corresponding ``AssertionType`` or ``None`` when the
        method name is not a recognized unittest assertion.
        """
        mapping = {
            "assertEqual": AssertionType.ASSERT_EQUAL,
            "assertTrue": AssertionType.ASSERT_TRUE,
            "assertFalse": AssertionType.ASSERT_FALSE,
            "assertIs": AssertionType.ASSERT_IS,
            "assertIsNone": AssertionType.ASSERT_IS_NONE,
            "assertIsNotNone": AssertionType.ASSERT_IS_NOT_NONE,
            "assertIn": AssertionType.ASSERT_IN,
            "assertNotIn": AssertionType.ASSERT_NOT_IN,
            "assertIsInstance": AssertionType.ASSERT_IS_INSTANCE,
            "assertNotIsInstance": AssertionType.ASSERT_NOT_IS_INSTANCE,
            "assertRaises": AssertionType.ASSERT_RAISES,
            "assertRaisesRegex": AssertionType.ASSERT_RAISES_REGEX,
            "assertDictEqual": AssertionType.ASSERT_DICT_EQUAL,
            "assertListEqual": AssertionType.ASSERT_LIST_EQUAL,
            "assertSetEqual": AssertionType.ASSERT_SET_EQUAL,
            "assertTupleEqual": AssertionType.ASSERT_TUPLE_EQUAL,
            "assertCountEqual": AssertionType.ASSERT_COUNT_EQUAL,
            "assertMultiLineEqual": AssertionType.ASSERT_MULTILINE_EQUAL,
            "assertSequenceEqual": AssertionType.ASSERT_SEQUENCE_EQUAL,
            "assertAlmostEqual": AssertionType.ASSERT_ALMOST_EQUAL,
            "assertGreater": AssertionType.ASSERT_GREATER,
            "assertGreaterEqual": AssertionType.ASSERT_GREATER_EQUAL,
            "assertLess": AssertionType.ASSERT_LESS,
            "assertLessEqual": AssertionType.ASSERT_LESS_EQUAL,
            "assertRegex": AssertionType.ASSERT_REGEX,
            "assertNotRegex": AssertionType.ASSERT_NOT_REGEX,
            "assertWarns": AssertionType.ASSERT_WARNS,
            "assertWarnsRegex": AssertionType.ASSERT_WARNS_REGEX,
            "assertLogs": AssertionType.ASSERT_LOGS,
            "assertNoLogs": AssertionType.ASSERT_NO_LOGS,
        }
        return mapping.get(method_name)

    def _analyze_setup_method(self, node: cst.FunctionDef, method_name: str) -> None:
        """Extract setup code from ``setUp``/``setUpClass`` and create a ``Fixture``.

        The extracted code is stored as strings in the ``Fixture`` for later
        emission by generators.
        """
        if self.current_class is None:
            return

        # Extract the code from the method body
        setup_code = []
        for stmt in node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                setup_code.append(cst.Module(body=[stmt]).code.strip())
            elif isinstance(stmt, cst.BaseCompoundStatement):
                setup_code.append(cst.Module(body=[stmt]).code.strip())

        # Create fixture
        if method_name == "setUpClass":
            fixture = Fixture(
                name="setup_class", scope=FixtureScope.CLASS, setup_code=setup_code, teardown_code=[], is_autouse=True
            )
            self.current_class.class_setup = fixture
        else:  # setUp
            fixture = Fixture(
                name="setup_method",
                scope=FixtureScope.FUNCTION,
                setup_code=setup_code,
                teardown_code=[],
                is_autouse=True,
            )
            self.current_class.instance_setup = fixture
        return

    def _analyze_teardown_method(self, node: cst.FunctionDef, method_name: str) -> None:
        """Extract teardown code from ``tearDown``/``tearDownClass`` and create a ``Fixture``.

        The extracted code is stored as strings in the ``Fixture`` for later
        emission by generators.
        """
        if self.current_class is None:
            return

        # Extract the code from the method body
        teardown_code = []
        for stmt in node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                teardown_code.append(cst.Module(body=[stmt]).code.strip())
            elif isinstance(stmt, cst.BaseCompoundStatement):
                teardown_code.append(cst.Module(body=[stmt]).code.strip())

        # Create fixture
        if method_name == "tearDownClass":
            fixture = Fixture(
                name="teardown_class",
                scope=FixtureScope.CLASS,
                setup_code=[],
                teardown_code=teardown_code,
                is_autouse=True,
            )
            self.current_class.class_teardown = fixture
        else:  # tearDown
            fixture = Fixture(
                name="teardown_method",
                scope=FixtureScope.FUNCTION,
                setup_code=[],
                teardown_code=teardown_code,
                is_autouse=True,
            )
            self.current_class.instance_teardown = fixture
        return

    def _analyze_test_method(self, node: cst.FunctionDef, method_name: str) -> None:
        """Create a ``TestMethod`` and collect assertions found in the body.

        The method's decorators and parameters are recorded on the IR
        ``TestMethod`` for use by downstream code generators.
        """
        if self.current_class is None:
            return

        # Create test method
        test_method = TestMethod(
            name=method_name,
            body=[],
            decorators=[
                cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=d.decorator)])]).code.strip()
                for d in node.decorators
            ],
        )

        # Store current method for assertion analysis
        old_method = self.current_method
        self.current_method = test_method

        # Visit method body to find assertions
        for stmt in node.body.body:
            stmt.visit(self)

        # Restore previous method
        self.current_method = old_method

        # Add method to class
        self.current_class.methods.append(test_method)

        # (Do not append class to module here to avoid duplicates)
        return

    def _analyze_assertion(self, node: cst.Call, assertion_type: AssertionType) -> None:
        """Create an ``Assertion`` IR node from a unittest assertion call.

        The call arguments are stringified into ``Expression`` objects for
        easier formatting by code generators.
        """
        if self.current_method is None:
            return

        # Extract arguments
        arguments = []
        for arg in node.args:
            # Create a module with just this expression to get its string representation
            if isinstance(arg.value, cst.BaseExpression):
                expr_module = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=arg.value)])])
                arguments.append(Expression(type="Argument", value=expr_module.code.strip()))
            else:
                # Fallback for non-expression arguments - this handles edge cases
                arguments.append(Expression(type="Argument", value=str(arg.value)))  # type: ignore

        # Create assertion
        assertion = Assertion(
            arguments=arguments, assertion_type=assertion_type, original_location={"line": getattr(node, "lineno", 0)}
        )

        # Add to current method
        self.current_method.body.append(assertion)
        return
