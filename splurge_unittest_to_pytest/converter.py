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
        self.has_unittest_content = False
        self.imports_to_remove: list[str] = []
        self.imports_to_add: list[str] = []
        
        # Track fixtures created from setUp methods
        self.setup_fixtures: dict[str, cst.FunctionDef] = {}
        self.teardown_cleanup: dict[str, list[cst.BaseStatement]] = {}
        self.setup_assignments: dict[str, cst.BaseExpression] = {}
        
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
        try:
            if m.matches(updated_node, m.ImportFrom(module=m.Name("unittest"))):
                # Remove unittest imports
                self.has_unittest_content = True
                return cst.RemovalSentinel.REMOVE
            return updated_node
        except Exception:
            # If conversion fails, return original node unchanged
            return original_node

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.Import | cst.RemovalSentinel:
        """Handle import statements."""
        try:
            for alias in updated_node.names:
                if m.matches(alias, m.ImportAlias(name=m.Name("unittest"))):
                    # Remove unittest imports
                    self.has_unittest_content = True
                    return cst.RemovalSentinel.REMOVE
            return updated_node
        except Exception:
            # If conversion fails, return original node unchanged
            return original_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Remove unittest.TestCase inheritance and convert class structure."""
        try:
            if updated_node.bases:
                # Check if any bases are unittest TestCase
                has_unittest_base = any(self._is_unittest_testcase(base) for base in updated_node.bases)
                if has_unittest_base:
                    self.has_unittest_content = True
                
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
            return original_node

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
                # Convert setup method to individual pytest fixtures
                return self._convert_setup_to_fixture(updated_node)
            elif self._is_teardown_method(method_name):
                # Convert teardown method by storing cleanup code
                return self._convert_teardown_to_fixture(updated_node)
            elif self._is_test_method(method_name) and self.has_unittest_content:
                # Only remove self/cls parameter from test methods if converting unittest content
                new_params, new_body = self._remove_method_self_references(updated_node)
                
                # Add fixture parameters to test methods
                fixture_params = self._get_fixture_params_for_test_method()
                if fixture_params:
                    # Create parameter objects for fixtures
                    fixture_param_objects = []
                    for fixture_name in fixture_params:
                        fixture_param_objects.append(
                            cst.Param(name=cst.Name(fixture_name))
                        )
                    # Combine existing params (excluding self) with fixture params
                    all_params = new_params + fixture_param_objects
                else:
                    all_params = new_params
                
                return updated_node.with_changes(
                    params=updated_node.params.with_changes(params=all_params),
                    body=new_body
                )
        except Exception:
            # If conversion fails, return original node unchanged
            return original_node
        
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
            return original_node
        
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
            return original_node
        
        return updated_node

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add necessary imports and fixtures at module level."""
        try:
            # Add pytest import if needed
            if self.needs_pytest_import:
                updated_node = self._add_pytest_import(updated_node)
            
            # Create fixtures from stored setUp assignments (if not already created)
            if self.setup_assignments and not self.setup_fixtures:
                self._create_fixtures_from_setup_assignments()
                updated_node = self._add_fixtures_to_module(updated_node)
            elif self.setup_fixtures:
                updated_node = self._add_fixtures_to_module(updated_node)
                
        except Exception:
            # If processing fails, return original node unchanged
            return original_node
        
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
                
        # Avoid adding if pytest is already imported
        for stmt in new_body:
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                first = stmt.body[0]
                if isinstance(first, cst.Import):
                    for alias in first.names:
                        if isinstance(alias.name, cst.Name) and alias.name.value == "pytest":
                            return module_node
                if isinstance(first, cst.ImportFrom) and isinstance(first.module, cst.Name):
                    if first.module.value == "pytest":
                        return module_node

        new_body.insert(insert_pos, pytest_import)
        return module_node.with_changes(body=new_body)

    def _create_fixtures_from_setup_assignments(self) -> None:
        """Create fixtures from stored setUp assignments and tearDown cleanup."""
        for attr_name, value_expr in self.setup_assignments.items():
            fixture_node = self._create_fixture_for_attribute(attr_name, value_expr)
            self.setup_fixtures[attr_name] = fixture_node
        
        self.needs_pytest_import = True

    def _add_fixtures_to_module(self, module_node: cst.Module) -> cst.Module:
        """Add created fixtures to the module."""
        if not self.setup_fixtures:
            return module_node
        
        new_body = list(module_node.body)
        
        # Find the position to insert fixtures (after imports, before classes/functions)
        insert_pos = 0
        for i, stmt in enumerate(new_body):
            if isinstance(stmt, cst.SimpleStatementLine) and isinstance(stmt.body[0], cst.ImportFrom):
                insert_pos = i + 1
            elif isinstance(stmt, cst.SimpleStatementLine) and isinstance(stmt.body[0], cst.Import):
                insert_pos = i + 1
            elif not (isinstance(stmt, cst.SimpleStatementLine) and 
                     (isinstance(stmt.body[0], cst.ImportFrom) or isinstance(stmt.body[0], cst.Import))):
                break
        
        # Insert fixtures at the determined position
        for fixture_name, fixture_node in self.setup_fixtures.items():
            # Add a blank line before each fixture for readability
            if insert_pos > 0:
                new_body.insert(insert_pos, cst.EmptyLine())
                insert_pos += 1
            
            new_body.insert(insert_pos, fixture_node)
            insert_pos += 1
        
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

    def _parse_setup_assignments(self, node: cst.FunctionDef) -> dict[str, cst.BaseExpression]:
        """Parse setUp method to find self.attribute = value assignments.
        
        Returns:
            Dictionary mapping attribute names to their assigned expressions
        """
        assignments = {}
        
        # Visit all assignment statements in the function body
        for stmt in node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # The assignment might be in stmt.body[0] or directly in stmt.body
                if len(stmt.body) > 0:
                    expr = stmt.body[0]
                    if isinstance(expr, cst.Assign):
                        # Check if assigning to self.attribute
                        if (len(expr.targets) == 1 and 
                            isinstance(expr.targets[0].target, cst.Attribute) and
                            isinstance(expr.targets[0].target.value, cst.Name) and
                            expr.targets[0].target.value.value == "self"):
                            
                            attr_name = expr.targets[0].target.attr.value
                            assignments[attr_name] = expr.value
        
        return assignments

    def _convert_setup_to_fixture(self, node: cst.FunctionDef) -> cst.RemovalSentinel:
        """Convert setUp method by storing assignments and creating fixtures immediately.
        
        Create fixtures immediately after parsing setUp assignments so they're available
        when processing test methods.
        """
        assignments = self._parse_setup_assignments(node)
        
        if not assignments:
            # No assignments found, remove the setUp method
            return cst.RemovalSentinel.REMOVE
        
        # Store assignments for fixture creation
        self.setup_assignments = assignments
        
        # Create fixtures immediately so they're available for test methods
        self._create_fixtures_from_setup_assignments()
        
        # Remove the original setUp method
        return cst.RemovalSentinel.REMOVE

    def _create_fixture_for_attribute(self, attr_name: str, value_expr: cst.BaseExpression) -> cst.FunctionDef:
        """Create a pytest fixture for a specific attribute."""
        # Check if there's teardown code for this fixture
        cleanup_statements = self.teardown_cleanup.get(attr_name, [])
        
        if cleanup_statements:
            # Use yield pattern with cleanup
            return self._create_fixture_with_cleanup(attr_name, value_expr, cleanup_statements)
        else:
            # Simple fixture without cleanup
            return self._create_simple_fixture(attr_name, value_expr)

    def _get_fixture_params_for_test_method(self) -> list[str]:
        """Get list of fixture names that should be parameters for test methods."""
        return list(self.setup_fixtures.keys())

    def _add_fixture_params_to_test_method(
        self, existing_params: cst.Parameters, fixture_names: list[str]
    ) -> cst.Parameters:
        """Add fixture parameters to test method signature."""
        # Create parameter objects for fixtures
        fixture_params = []
        for fixture_name in fixture_names:
            fixture_params.append(
                cst.Param(name=cst.Name(fixture_name))
            )
        
        # Combine existing params (excluding self) with fixture params
        all_params = fixture_params
        
        return cst.Parameters(params=all_params)

    def _convert_teardown_to_fixture(self, node: cst.FunctionDef) -> cst.RemovalSentinel:
        """Convert tearDown method by integrating cleanup with setup fixtures.
        
        This method processes tearDown and creates/updates fixtures with cleanup.
        """
        # Store the teardown body statements with self references removed
        remover = SelfReferenceRemover({"self"})
        cleanup_statements = []
        for stmt in node.body.body:
            cleanup_statements.append(stmt.visit(remover))
        
        # If we have setup assignments, create fixtures with cleanup
        if self.setup_assignments:
            self._create_fixtures_with_cleanup(cleanup_statements)
        else:
            # Store cleanup for later if setUp hasn't been processed yet
            # Associate cleanup with all current setup fixtures
            for fixture_name in self.setup_fixtures.keys():
                if fixture_name not in self.teardown_cleanup:
                    self.teardown_cleanup[fixture_name] = []
                self.teardown_cleanup[fixture_name].extend(cleanup_statements)
        
        # Remove the original tearDown method
        return cst.RemovalSentinel.REMOVE
    
    def _create_fixtures_with_cleanup(self, cleanup_statements: list[cst.BaseStatement]) -> None:
        """Create fixtures from setup assignments with tearDown cleanup integration."""
        for attr_name, value_expr in self.setup_assignments.items():
            # Check if this attribute appears in cleanup statements
            relevant_cleanup = self._extract_relevant_cleanup(cleanup_statements, attr_name)
            
            if relevant_cleanup:
                # Create fixture with yield and cleanup
                fixture_node = self._create_fixture_with_cleanup(attr_name, value_expr, relevant_cleanup)
            else:
                # Create simple fixture with return
                fixture_node = self._create_simple_fixture(attr_name, value_expr)
            
            self.setup_fixtures[attr_name] = fixture_node
        
        self.needs_pytest_import = True
    
    def _extract_relevant_cleanup(self, cleanup_statements: list[cst.BaseStatement], attr_name: str) -> list[cst.BaseStatement]:
        """Extract cleanup statements that reference the given attribute."""
        relevant_statements = []
        
        for stmt in cleanup_statements:
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                expr = stmt.body[0]
                if isinstance(expr, cst.Expr) and isinstance(expr.value, cst.Call):
                    # Check if the call references the attribute
                    call = expr.value
                    # Treat method calls on the attribute as cleanup, e.g. self.value.close()
                    func = call.func
                    # Method call on attribute, e.g., self.value.close()
                    if isinstance(func, cst.Attribute) and self._references_attribute(func.value, attr_name):
                        relevant_statements.append(stmt)
                        continue
                    # Or any argument references the attribute (e.g., shutil.rmtree(self.temp_dir))
                    for arg in call.args:
                        if self._references_attribute(arg.value, attr_name):
                            relevant_statements.append(stmt)
                            break
                elif isinstance(expr, cst.Assign):
                    # Check if the assignment target references the attribute
                    for target in expr.targets:
                        # Assign.targets contains AssignTarget nodes; the actual expression
                        # is in the 'target' attribute. Use that when present so we can
                        # correctly detect names/attributes like 'value' or 'self.value'.
                        target_expr = getattr(target, "target", target)
                        if self._references_attribute(target_expr, attr_name):
                            relevant_statements.append(stmt)
                            break
        
        return relevant_statements
    
    def _references_attribute(self, expr: cst.BaseExpression, attr_name: str) -> bool:
        """Check if an expression references a specific attribute."""
        # Direct attribute or name match
        if isinstance(expr, cst.Attribute):
            return expr.attr.value == attr_name
        if isinstance(expr, cst.Name):
            return expr.value == attr_name

        # Recursively inspect common expression containers
        # Calls: inspect func and args
        if isinstance(expr, cst.Call):
            if self._references_attribute(expr.func, attr_name):
                return True
            for a in expr.args:
                if self._references_attribute(a.value, attr_name):
                    return True
            return False

        # Subscript/indexing
        if isinstance(expr, cst.Subscript):
            if self._references_attribute(expr.value, attr_name):
                return True
            for s in expr.slice:
                # slice can be Index or Slice objects
                inner = getattr(s, 'slice', None) or getattr(s, 'value', None) or s
                if isinstance(inner, cst.BaseExpression) and self._references_attribute(inner, attr_name):
                    return True
            return False

        # Binary operations, comparisons, boolean ops
        if isinstance(expr, (cst.BinaryOperation, cst.Comparison, cst.BooleanOperation)):
            # These nodes have left/right or comparisons/values attributes
            parts = []
            if hasattr(expr, 'left'):
                parts.append(expr.left)
            if hasattr(expr, 'right'):
                parts.append(expr.right)
            if hasattr(expr, 'comparisons'):
                for comp in expr.comparisons:
                    parts.append(getattr(comp, 'comparison', None) or getattr(comp, 'operator', None))
            for part in parts:
                if isinstance(part, cst.BaseExpression) and self._references_attribute(part, attr_name):
                    return True
            return False

        # Assignments and targets handled elsewhere; for other nodes, try to walk common containers
        # Sequence/tuple/list literals
        if isinstance(expr, (cst.Tuple, cst.List, cst.Set)):
            for e in expr.elements:
                val = getattr(e, 'value', e)
                if isinstance(val, cst.BaseExpression) and self._references_attribute(val, attr_name):
                    return True
            return False

        # Fallback: not found
        return False
    
    def _create_fixture_with_cleanup(self, attr_name: str, value_expr: cst.BaseExpression, cleanup_statements: list[cst.BaseStatement]) -> cst.FunctionDef:
        """Create a fixture with yield pattern and cleanup."""
        # Create the @pytest.fixture decorator
        fixture_decorator = cst.Decorator(
            decorator=cst.Call(
                func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture"))
            )
        )
        
        # Create fixture function body with yield and cleanup
        yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=value_expr))])
        body = cst.IndentedBlock(body=[yield_stmt] + cleanup_statements)
        
        # Create the fixture function
        fixture_func = cst.FunctionDef(
            name=cst.Name(attr_name),
            params=cst.Parameters(),
            body=body,
            decorators=[fixture_decorator],
            returns=None,
            asynchronous=None
        )
        
        return fixture_func
    
    def _create_simple_fixture(self, attr_name: str, value_expr: cst.BaseExpression) -> cst.FunctionDef:
        """Create a simple fixture with return (no cleanup needed)."""
        # Create the @pytest.fixture decorator
        fixture_decorator = cst.Decorator(
            decorator=cst.Call(
                func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture"))
            )
        )
        
        # Create fixture function body with return
        return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=value_expr)])
        body = cst.IndentedBlock(body=[return_stmt])
        
        # Create the fixture function
        fixture_func = cst.FunctionDef(
            name=cst.Name(attr_name),
            params=cst.Parameters(),
            body=body,
            decorators=[fixture_decorator],
            returns=None,
            asynchronous=None
        )
        
        return fixture_func