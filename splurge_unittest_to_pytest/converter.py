"""Core conversion logic for unittest to pytest transformation."""

from typing import Sequence

import libcst as cst
from libcst import matchers as m
from libcst._flatten_sentinel import FlattenSentinel
from libcst._removal_sentinel import RemovalSentinel


class SelfReferenceRemover(cst.CSTTransformer):
    """Remove self references from attribute accesses."""

    def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.Attribute | cst.Name:
        """Convert self.attribute to just attribute."""
        if m.matches(updated_node.value, m.Name("self")):
            # Replace self.attribute with just attribute
            return updated_node.attr
        return updated_node


class UnittestToPytestTransformer(cst.CSTTransformer):
    """Transform unittest-style tests to pytest-style tests."""

    def __init__(self) -> None:
        """Initialize the transformer."""
        self.needs_pytest_import = False
        self.imports_to_remove: list[str] = []
        self.imports_to_add: list[str] = []

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

        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef | cst.RemovalSentinel:
        """Convert setUp/tearDown methods to pytest fixtures and remove self from test methods."""
        if updated_node.name.value == "setUp":
            # Convert setUp to pytest fixture
            return self._convert_setup_to_fixture(updated_node)
        elif updated_node.name.value == "tearDown":
            # Convert tearDown to pytest fixture with yield
            return self._convert_teardown_to_fixture(updated_node)
        elif updated_node.name.value.startswith("test_"):
            # Remove self parameter from test methods and self references from body
            new_params = []
            if updated_node.params.params:
                # Skip the first parameter (self)
                new_params = list(updated_node.params.params[1:])
            
            # Remove self references from the function body
            new_body = self._remove_self_references(updated_node.body)
            
            return updated_node.with_changes(
                params=updated_node.params.with_changes(params=new_params),
                body=new_body
            )
        return updated_node

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Handle call expressions."""
        return updated_node

    def leave_Expr(
        self, original_node: cst.Expr, updated_node: cst.Expr
    ) -> cst.BaseSmallStatement | FlattenSentinel[cst.BaseSmallStatement] | RemovalSentinel:
        """Convert unittest assertion expressions to pytest assert statements."""
        if isinstance(updated_node.value, cst.Call):
            call_node = updated_node.value
            if isinstance(call_node.func, cst.Attribute):
                if isinstance(call_node.func.value, cst.Name):
                    if call_node.func.value.value == "self":
                        method_name = call_node.func.attr.value
                        args = call_node.args
                        
                        # Skip assertRaises methods - handle them in leave_With
                        if method_name in ("assertRaises", "assertRaisesRegex"):
                            return updated_node
                            
                        # Handle other assertion methods
                        conversion_result = self._convert_assertion(method_name, args)
                        if conversion_result is not None and isinstance(conversion_result, cst.BaseSmallStatement):
                            return conversion_result
        
        return updated_node

    def leave_With(
        self, original_node: cst.With, updated_node: cst.With
    ) -> cst.With:
        """Convert unittest assertRaises context managers to pytest.raises."""
        if updated_node.items:
            item = updated_node.items[0]
            if isinstance(item.item, cst.Call):
                call_node = item.item
                if isinstance(call_node.func, cst.Attribute):
                    if isinstance(call_node.func.value, cst.Name):
                        if call_node.func.value.value == "self":
                            method_name = call_node.func.attr.value
                            if method_name in ("assertRaises", "assertRaisesRegex"):
                                # Convert to pytest.raises
                                self.needs_pytest_import = True
                                if method_name == "assertRaises":
                                    new_item = cst.WithItem(
                                        item=cst.Call(
                                            func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")),
                                            args=call_node.args,
                                        )
                                    )
                                else:  # assertRaisesRegex
                                    new_item = cst.WithItem(
                                        item=cst.Call(
                                            func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")),
                                            args=[
                                                call_node.args[0],
                                                cst.Arg(keyword=cst.Name("match"), value=call_node.args[1].value),
                                            ] if len(call_node.args) >= 2 else call_node.args,
                                        )
                                    )
                                return updated_node.with_changes(items=[new_item])
        
        return updated_node

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add necessary imports at module level."""
        if self.needs_pytest_import:
            # Add pytest import if needed
            pytest_import = cst.SimpleStatementLine(
                body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])]
            )
            
            # Find the position to insert import (after existing imports)
            new_body = list(updated_node.body)
            insert_pos = 0
            
            for i, stmt in enumerate(new_body):
                if isinstance(stmt, cst.SimpleStatementLine):
                    # Check if this is an import statement
                    if stmt.body and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom)):
                        insert_pos = i + 1
                elif isinstance(stmt, cst.ImportFrom):
                    insert_pos = i + 1
                        
            new_body.insert(insert_pos, pytest_import)
            updated_node = updated_node.with_changes(body=new_body)

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

    def _convert_assertion(
        self, method_name: str, args: Sequence[cst.Arg]
    ) -> cst.BaseSmallStatement | None:
        """Convert unittest assertion methods to pytest assertions."""
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
        return None

    def _assert_equal(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertEqual to assert ==."""
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.Equal(), comparator=args[1].value)
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_not_equal(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertNotEqual to assert !=."""
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[
                        cst.ComparisonTarget(operator=cst.NotEqual(), comparator=args[1].value)
                    ],
                )
            )
        return cst.Assert(test=cst.Name("False"))

    def _assert_true(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertTrue to assert."""
        if len(args) >= 1:
            return cst.Assert(test=args[0].value)
        return cst.Assert(test=cst.Name("False"))

    def _assert_false(self, args: Sequence[cst.Arg]) -> cst.Assert:
        """Convert assertFalse to assert not."""
        if len(args) >= 1:
            return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=args[0].value))
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

    def _remove_self_references(self, node: cst.CSTNode) -> cst.CSTNode:
        """Remove self references from attribute accesses in fixture bodies."""
        return node.visit(SelfReferenceRemover())

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

        # Remove self parameter from fixture function
        new_params = []
        if node.params.params:
            # Skip the first parameter (self)
            new_params = list(node.params.params[1:])

        # Remove self references from the function body
        new_body = self._remove_self_references(node.body)

        return node.with_changes(
            name=cst.Name("setup_fixture"),
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

        # Remove self parameter from fixture function
        new_params = []
        if node.params.params:
            # Skip the first parameter (self)
            new_params = list(node.params.params[1:])

        # Convert tearDown body to use yield pattern
        yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield())])
        body_statements = node.body.body
        new_body = cst.IndentedBlock(body=[yield_stmt] + list(body_statements))  # type: ignore

        # Remove self references from the function body
        new_body = self._remove_self_references(new_body)

        return node.with_changes(
            name=cst.Name("teardown_fixture"),
            decorators=decorators,
            params=node.params.with_changes(params=new_params),
            body=new_body
        )