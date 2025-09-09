"""Core conversion logic for unittest to pytest transformation."""

from typing import Sequence

import libcst as cst
from libcst import matchers as m


class SelfReferenceRemover(cst.CSTTransformer):
    """Remove self/cls references from attribute accesses."""
    
    def __init__(self, param_names: set[str] | None = None):
        """Initialize with parameter names to remove.
        
        Args:
            param_names: Set of parameter names to remove (defaults to {'self', 'cls'})
        """
        self.param_names = param_names or {"self", "cls"}

    def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.Attribute | cst.Name:
        """Convert self.attribute or cls.attribute to just attribute."""
        if (isinstance(updated_node.value, cst.Name) and 
            updated_node.value.value in self.param_names):
            # Replace self.attribute or cls.attribute with just attribute
            return updated_node.attr
        return updated_node


class UnittestToPytestTransformer(cst.CSTTransformer):
    """Transform unittest-style tests to pytest-style tests."""

    def __init__(self) -> None:
        """Initialize the transformer."""
        self.needs_pytest_import = False
        self.imports_to_remove: list[str] = []
        self.imports_to_add: list[str] = []
        
        # Configurable method name patterns
        self._setup_patterns = {
            "setup", "setUp", "set_up", "setup_method", "setUp_method",
            "before_each", "beforeEach", "before_test", "beforeTest"
        }
        self._teardown_patterns = {
            "teardown", "tearDown", "tear_down", "teardown_method", "tearDown_method",
            "after_each", "afterEach", "after_test", "afterTest"
        }
        self._test_patterns = {
            "test_", "test", "should_", "when_", "given_", "it_", "spec_"
        }

    @property
    def setup_patterns(self) -> set[str]:
        """Get the current setup method name patterns."""
        return self._setup_patterns.copy()

    @property
    def teardown_patterns(self) -> set[str]:
        """Get the current teardown method name patterns."""
        return self._teardown_patterns.copy()

    @property
    def test_patterns(self) -> set[str]:
        """Get the current test method name patterns."""
        return self._test_patterns.copy()

    def add_setup_pattern(self, pattern: str) -> None:
        """Add a new setup method name pattern.
        
        Args:
            pattern: The pattern to add (e.g., "before_all", "setup_class")
        """
        if isinstance(pattern, str) and pattern.strip():
            # Store patterns in lowercase for case-insensitive matching
            self._setup_patterns.add(pattern.strip().lower())

    def add_teardown_pattern(self, pattern: str) -> None:
        """Add a new teardown method name pattern.
        
        Args:
            pattern: The pattern to add (e.g., "after_all", "teardown_class")
        """
        if isinstance(pattern, str) and pattern.strip():
            # Store patterns in lowercase for case-insensitive matching
            self._teardown_patterns.add(pattern.strip().lower())

    def add_test_pattern(self, pattern: str) -> None:
        """Add a new test method name pattern.
        
        Args:
            pattern: The pattern to add (e.g., "describe_", "context_")
        """
        if isinstance(pattern, str) and pattern.strip():
            # Store patterns as-is for prefix matching
            self._test_patterns.add(pattern.strip())

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        """Handle import statements."""
        if m.matches(updated_node, m.ImportFrom(module=m.Name("unittest"))):
            # Remove unittest imports
            return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.Import | cst.RemovalSentinel:
        """Handle import statements."""
        for alias in updated_node.names:
            if m.matches(alias, m.ImportAlias(name=m.Name("unittest"))):
                # Remove unittest imports
                return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Remove unittest.TestCase inheritance and convert class structure."""
        try:
            if updated_node.bases:
                # Filter out unittest.TestCase inheritance
                new_bases = []
                for base in updated_node.bases:
                    if not self._is_unittest_testcase(base):
                        new_bases.append(base)

                # If no bases remain, create a simple class without inheritance
                if not new_bases:
                    updated_node = updated_node.with_changes(bases=[])
                else:
                    updated_node = updated_node.with_changes(bases=new_bases)
        except Exception:
            # If conversion fails, return original node unchanged
            return updated_node

        return updated_node

        return updated_node

    def _should_remove_first_param(self, node: cst.FunctionDef) -> bool:
        """Determine if the first parameter should be removed based on method type."""
        if not node.params.params:
            return False
            
        first_param = node.params.params[0]
        first_param_name = first_param.name.value if hasattr(first_param, 'name') else ""
        
        # Check for decorators that indicate method type
        has_classmethod = any(
            (isinstance(decorator, cst.Decorator) and 
             isinstance(decorator.decorator, cst.Name) and 
             decorator.decorator.value == "classmethod")
            for decorator in (node.decorators or [])
        )
        
        has_staticmethod = any(
            (isinstance(decorator, cst.Decorator) and 
             isinstance(decorator.decorator, cst.Name) and 
             decorator.decorator.value == "staticmethod")
            for decorator in (node.decorators or [])
        )
        
        # For staticmethods, remove no parameters (they don't have self/cls)
        if has_staticmethod:
            return False
            
        # For classmethods, only remove if first param is 'cls'
        if has_classmethod:
            return first_param_name == "cls"
            
        # For regular instance methods, remove if first param is 'self'
        return first_param_name == "self"

    def _remove_method_self_references(self, node: cst.FunctionDef) -> tuple[list[cst.Param], cst.BaseSuite]:
        """Remove self/cls parameters and references based on method type."""
        new_params = list(node.params.params)
        new_body = node.body
        
        if self._should_remove_first_param(node):
            # Get the parameter name being removed
            first_param = node.params.params[0]
            param_name = first_param.name.value if hasattr(first_param, 'name') else ""
            
            # Remove the first parameter (self/cls)
            new_params = new_params[1:]
            
            # Remove self/cls references from the function body
            remover = SelfReferenceRemover({param_name})
            new_body = node.body.visit(remover)
        
        return new_params, new_body

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef | cst.RemovalSentinel:
        """Convert setUp/tearDown methods to pytest fixtures and remove self from test methods."""
        try:
            method_name = updated_node.name.value
            
            if self._is_setup_method(method_name):
                # Convert setup method to pytest fixture
                return self._convert_setup_to_fixture(updated_node)
            elif self._is_teardown_method(method_name):
                # Convert teardown method to pytest fixture with yield
                return self._convert_teardown_to_fixture(updated_node)
            elif self._is_test_method(method_name):
                # Remove self/cls parameter from test methods and self references from body
                new_params, new_body = self._remove_method_self_references(updated_node)
                
                return updated_node.with_changes(
                    params=updated_node.params.with_changes(params=new_params),
                    body=new_body
                )
        except Exception:
            # If conversion fails, return original node unchanged
            return updated_node
        
        return updated_node

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Handle call expressions."""
        return updated_node

    def leave_Expr(
        self, original_node: cst.Expr, updated_node: cst.Expr
    ) -> cst.BaseSmallStatement | cst.FlattenSentinel[cst.BaseSmallStatement] | cst.RemovalSentinel:
        """Convert unittest assertion expressions to pytest assert statements."""
        try:
            if isinstance(updated_node.value, cst.Call):
                conversion_result = self._convert_self_assertion_to_pytest(updated_node.value)
                if conversion_result is not None:
                    return conversion_result
        except Exception:
            # If conversion fails, return original node unchanged
            return updated_node
        
        return updated_node

    def leave_With(
        self, original_node: cst.With, updated_node: cst.With
    ) -> cst.With:
        """Convert unittest assertRaises context managers to pytest.raises."""
        try:
            if not updated_node.items:
                return updated_node
                
            item = updated_node.items[0]
            if not isinstance(item.item, cst.Call):
                return updated_node
                
            method_name = self._is_assert_raises_context_manager(item.item)
            if method_name:
                new_item = self._create_pytest_raises_item(method_name, item.item.args)
                return updated_node.with_changes(items=[new_item])
        except Exception:
            # If conversion fails, return original node unchanged
            return updated_node
        
        return updated_node

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add necessary imports at module level."""
        try:
            if self.needs_pytest_import:
                return self._add_pytest_import(updated_node)
        except Exception:
            # If import addition fails, return original node unchanged
            return updated_node
        
        return updated_node

    def _is_unittest_testcase(self, base: cst.Arg) -> bool:
        """Check if base class is unittest.TestCase."""
        if isinstance(base.value, cst.Attribute):
            if (isinstance(base.value.value, cst.Name) and 
                base.value.value.value == "unittest" and
                base.value.attr.value == "TestCase"):
                return True
        elif isinstance(base.value, cst.Name):
            if base.value.value == "TestCase":
                return True
        return False

    def _normalize_method_name(self, name: str) -> str:
        """Normalize method name for pattern matching (convert camelCase to snake_case)."""
        import re
        # Convert camelCase to snake_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _is_setup_method(self, method_name: str) -> bool:
        """Check if method name matches setup patterns (case insensitive)."""
        method_lower = method_name.lower()
        method_normalized = self._normalize_method_name(method_name)
        
        return any(
            pattern.lower() in method_lower or 
            pattern.lower() in method_normalized or
            self._normalize_method_name(pattern) in method_normalized
            for pattern in self._setup_patterns
        )

    def _is_teardown_method(self, method_name: str) -> bool:
        """Check if method name matches teardown patterns (case insensitive)."""
        method_lower = method_name.lower()
        method_normalized = self._normalize_method_name(method_name)
        
        return any(
            pattern.lower() in method_lower or 
            pattern.lower() in method_normalized or
            self._normalize_method_name(pattern) in method_normalized
            for pattern in self._teardown_patterns
        )

    def _is_test_method(self, method_name: str) -> bool:
        """Check if method name matches test patterns (case insensitive)."""
        method_lower = method_name.lower()
        method_normalized = self._normalize_method_name(method_name)
        
        return any(
            pattern.lower() in method_lower or 
            pattern.lower() in method_normalized or
            self._normalize_method_name(pattern) in method_normalized
            for pattern in self._test_patterns
        )

    def _convert_assertion(
        self, method_name: str, args: Sequence[cst.Arg]
    ) -> cst.BaseSmallStatement | None:
        """Convert unittest assertion methods to pytest assertions."""
        try:
            # Skip assertRaises methods - handled in leave_With
            if method_name in ("assertRaises", "assertRaisesRegex"):
                return None
                
            assertions_map = {
                "assertEqual": self._assert_equal,
                "assertNotEqual": self._assert_not_equal,
                "assertTrue": self._assert_true,
                "assertFalse": self._assert_false,
                "assertIsNone": self._assert_is_none,
                "assertIsNotNone": self._assert_is_not_none,
                "assertIn": self._assert_in,
                "assertNotIn": self._assert_not_in,
                "assertIsInstance": self._assert_is_instance,
                "assertNotIsInstance": self._assert_not_is_instance,
                "assertGreater": self._assert_greater,
                "assertGreaterEqual": self._assert_greater_equal,
                "assertLess": self._assert_less,
                "assertLessEqual": self._assert_less_equal,
            }

            converter = assertions_map.get(method_name)
            if converter:
                return converter(args)
        except Exception:
            # If conversion fails, return None to skip conversion
            return None
        
        return None

    def _assert_equal(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertEqual to assert ==."""
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[
                            cst.ComparisonTarget(operator=cst.Equal(), comparator=args[1].value)
                        ],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_not_equal(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertNotEqual to assert !=."""
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[
                            cst.ComparisonTarget(operator=cst.NotEqual(), comparator=args[1].value)
                        ],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_true(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertTrue to assert."""
        try:
            if len(args) >= 1:
                return cst.Assert(test=args[0].value)
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_false(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertFalse to assert not."""
        try:
            if len(args) >= 1:
                return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=args[0].value))
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_is_none(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertIsNone to assert ... is None."""
        if len(args) >= 1:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.Is(), comparator=cst.Name("None"))
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_is_not_none(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertIsNotNone to assert ... is not None."""
        if len(args) >= 1:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_in(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertIn to assert ... in ..."""
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.In(), comparator=args[1].value)
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_not_in(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertNotIn to assert ... not in ..."""
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.NotIn(), comparator=args[1].value)
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_is_instance(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertIsInstance to assert isinstance(...)."""
        if len(args) >= 2:
            isinstance_call = cst.Call(
                func=cst.Name("isinstance"), args=[args[0], args[1]]
            )
            return cst.Assert(test=isinstance_call)
        return cst.Assert(test=cst.Name("False"))

    def _assert_not_is_instance(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertNotIsInstance to assert not isinstance(...)."""
        if len(args) >= 2:
            isinstance_call = cst.Call(
                func=cst.Name("isinstance"), args=[args[0], args[1]]
            )
            return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=isinstance_call))
        return cst.Assert(test=cst.Name("False"))

    def _assert_greater(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertGreater to assert ... > ..."""
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.GreaterThan(), comparator=args[1].value)
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_greater_equal(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertGreaterEqual to assert ... >= ..."""
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.GreaterThanEqual(), comparator=args[1].value)
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_less(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertLess to assert ... < ..."""
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.LessThan(), comparator=args[1].value)
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_less_equal(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertLessEqual to assert ... <= ..."""
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.LessThanEqual(), comparator=args[1].value)
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_raises(self, args: Sequence[cst.Arg]) -> cst.Call:
        """Convert assertRaises to pytest.raises context manager."""
        self.needs_pytest_import = True
        if len(args) >= 1:
            return cst.Call(
                func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")),
                args=[args[0]],
            )
        return cst.Call(
            func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")),
            args=[cst.Arg(value=cst.Name("Exception"))],
        )

    def _assert_raises_regex(self, args: Sequence[cst.Arg]) -> cst.Call:
        """Convert assertRaisesRegex to pytest.raises with match parameter."""
        self.needs_pytest_import = True
        if len(args) >= 2:
            return cst.Call(
                func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")),
                args=[
                    args[0],
                    cst.Arg(keyword=cst.Name("match"), value=args[1].value),
                ],
            )
        return self._assert_raises(args[:1] if args else [])

    def _is_assert_raises_context_manager(self, call_node: cst.Call) -> str | None:
        """Check if call is assertRaises/assertRaisesRegex and return method name."""
        call_info = self._is_self_call(call_node)
        if call_info:
            method_name, _ = call_info
            if method_name in ("assertRaises", "assertRaisesRegex"):
                return method_name
        return None

    def _create_pytest_raises_item(self, method_name: str, args: Sequence[cst.Arg]) -> cst.WithItem:
        """Create pytest.raises WithItem from assertRaises/assertRaisesRegex."""
        self.needs_pytest_import = True
        
        if method_name == "assertRaises":
            return cst.WithItem(
                item=cst.Call(
                    func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")),
                    args=args,
                )
            )
        else:  # assertRaisesRegex
            return cst.WithItem(
                item=cst.Call(
                    func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")),
                    args=[
                        args[0],
                        cst.Arg(keyword=cst.Name("match"), value=args[1].value),
                    ] if len(args) >= 2 else args,
                )
            )
    def _remove_self_references(self, node: cst.CSTNode) -> cst.CSTNode:
        """Remove self/cls references from attribute accesses in fixture bodies."""
        return node.visit(SelfReferenceRemover())

    def _add_pytest_import(self, module_node: cst.Module) -> cst.Module:
        """Add pytest import to module at appropriate position."""
        # Add pytest import if needed
        pytest_import = cst.SimpleStatementLine(
            body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])]
        )
        
        # Find the position to insert import (after existing imports)
        new_body = list(module_node.body)
        insert_pos = 0
        
        for i, stmt in enumerate(new_body):
            if isinstance(stmt, cst.SimpleStatementLine):
                # Check if this is an import statement
                if stmt.body and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom)):
                    insert_pos = i + 1
            elif isinstance(stmt, cst.ImportFrom):
                insert_pos = i + 1
                
        new_body.insert(insert_pos, pytest_import)
        return module_node.with_changes(body=new_body)

    def _is_self_call(self, call_node: cst.Call) -> tuple[str, Sequence[cst.Arg]] | None:
        """Check if call is a self.method() call and return method name and args."""
        try:
            if isinstance(call_node.func, cst.Attribute):
                if isinstance(call_node.func.value, cst.Name):
                    if call_node.func.value.value == "self":
                        method_name = call_node.func.attr.value
                        return method_name, call_node.args
        except Exception:
            pass
        return None

    def _should_skip_assertion_conversion(self, method_name: str) -> bool:
        """Check if assertion method should be skipped (handled elsewhere)."""
        return method_name in ("assertRaises", "assertRaisesRegex")

    def _convert_self_assertion_to_pytest(
        self, call_node: cst.Call
    ) -> cst.BaseSmallStatement | None:
        """Convert self.assertion() calls to pytest assertions."""
        try:
            call_info = self._is_self_call(call_node)
            if not call_info:
                return None
                
            method_name, args = call_info
            
            if self._should_skip_assertion_conversion(method_name):
                return None
                
            return self._convert_assertion(method_name, args)
        except Exception:
            return None

    def _convert_setup_to_fixture(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Convert setUp method to pytest fixture."""
        # Create the decorator manually
        autouse_arg = cst.Arg(
            keyword=cst.Name("autouse"), 
            value=cst.Name("True"),
            equal=cst.AssignEqual(
                whitespace_before=cst.SimpleWhitespace(''),
                whitespace_after=cst.SimpleWhitespace('')
            )
        )
        fixture_call = cst.Call(
            func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")),
            args=[autouse_arg]
        )
        fixture_decorator = cst.Decorator(decorator=fixture_call)

        decorators = list(node.decorators) if node.decorators else []
        decorators.append(fixture_decorator)

        self.needs_pytest_import = True

        # Remove self/cls parameter from fixture function based on method type
        new_params, new_body = self._remove_method_self_references(node)

        return node.with_changes(
            name=cst.Name(f"{node.name.value}_fixture"),
            decorators=decorators,
            params=node.params.with_changes(params=new_params),
            body=new_body
        )

    def _convert_teardown_to_fixture(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Convert tearDown method to pytest fixture with yield."""
        # Create the decorator manually
        autouse_arg = cst.Arg(
            keyword=cst.Name("autouse"), 
            value=cst.Name("True"),
            equal=cst.AssignEqual(
                whitespace_before=cst.SimpleWhitespace(''),
                whitespace_after=cst.SimpleWhitespace('')
            )
        )
        fixture_call = cst.Call(
            func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")),
            args=[autouse_arg]
        )
        fixture_decorator = cst.Decorator(decorator=fixture_call)

        decorators = list(node.decorators) if node.decorators else []
        decorators.append(fixture_decorator)

        self.needs_pytest_import = True

        # Remove self/cls parameter from fixture function based on method type
        new_params, new_body = self._remove_method_self_references(node)

        # Convert tearDown body to use yield pattern
        yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield())])
        body_statements = new_body.body
        new_body = cst.IndentedBlock(body=[yield_stmt] + list(body_statements))  # type: ignore

        return node.with_changes(
            name=cst.Name(f"{node.name.value}_fixture"),
            decorators=decorators,
            params=node.params.with_changes(params=new_params),
            body=new_body
        )