"""Core conversion logic for unittest to pytest transformation."""

from typing import Any, Dict, List, Optional, Sequence, Union

import libcst as cst
from libcst import matchers as m


class UnittestToPytestTransformer(cst.CSTTransformer):
    """Transform unittest-style tests to pytest-style tests."""

    def __init__(self) -> None:
        """Initialize the transformer."""
        self.needs_pytest_import = False
        self.imports_to_remove: List[str] = []
        self.imports_to_add: List[str] = []

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> Union[cst.ImportFrom, cst.RemovalSentinel]:
        """Handle import statements."""
        if m.matches(updated_node, m.ImportFrom(module=m.Name("unittest"))):
            # Remove unittest imports
            return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> Union[cst.Import, cst.RemovalSentinel]:
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
    ) -> Union[cst.FunctionDef, cst.RemovalSentinel]:
        """Convert setUp/tearDown methods to pytest fixtures."""
        if updated_node.name.value == "setUp":
            # Convert setUp to pytest fixture
            return self._convert_setup_to_fixture(updated_node)
        elif updated_node.name.value == "tearDown":
            # Convert tearDown to pytest fixture with yield
            return self._convert_teardown_to_fixture(updated_node)
        return updated_node

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> Union[cst.Call, cst.Assert, cst.With]:
        """Convert unittest assertion methods to pytest assertions."""
        if not isinstance(updated_node.func, cst.Attribute):
            return updated_node

        if not isinstance(updated_node.func.value, cst.Name):
            return updated_node

        if updated_node.func.value.value != "self":
            return updated_node

        method_name = updated_node.func.attr.value
        args = updated_node.args

        # Handle different assertion methods
        conversion_result = self._convert_assertion(method_name, args)
        if conversion_result is not None:
            return conversion_result

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
                if isinstance(stmt, (cst.SimpleStatementLine, cst.ImportFrom)):
                    if any(isinstance(s, (cst.Import, cst.ImportFrom)) for s in 
                          (stmt.body if hasattr(stmt, 'body') else [stmt])):
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
    ) -> Optional[Union[cst.Assert, cst.With, cst.Call]]:
        """Convert unittest assertion methods to pytest assertions."""
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
            "assertRaises": self._assert_raises,
            "assertRaisesRegex": self._assert_raises_regex,
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

    def _convert_setup_to_fixture(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Convert setUp method to pytest fixture."""
        # Add pytest.fixture decorator
        fixture_decorator = cst.Decorator(
            decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture"))
        )
        
        decorators = list(node.decorators) if node.decorators else []
        decorators.append(fixture_decorator)
        
        self.needs_pytest_import = True
        
        return node.with_changes(
            name=cst.Name("setup_method"),
            decorators=decorators
        )

    def _convert_teardown_to_fixture(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Convert tearDown method to pytest fixture with yield."""
        # Add pytest.fixture decorator with autouse=True
        fixture_decorator = cst.Decorator(
            decorator=cst.Call(
                func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")),
                args=[cst.Arg(keyword=cst.Name("autouse"), value=cst.Name("True"))],
            )
        )
        
        decorators = list(node.decorators) if node.decorators else []
        decorators.append(fixture_decorator)
        
        self.needs_pytest_import = True
        
        # Convert tearDown body to use yield pattern
        yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield())])
        new_body = cst.IndentedBlock(body=[yield_stmt] + list(node.body.body))
        
        return node.with_changes(
            name=cst.Name("teardown_method"),
            decorators=decorators,
            body=new_body
        )