"""Core conversion logic for unittest to pytest transformation."""

from typing import Sequence, Any, cast
import warnings

import libcst as cst


# Reuse the moved helpers from converter.helpers during decomposition
from .converter.helpers import SelfReferenceRemover
from .converter.raises import (
    make_pytest_raises_call,
    make_pytest_raises_regex_call,
    create_pytest_raises_withitem,
)
from .converter.fixtures import (
    create_simple_fixture,
    parse_setup_assignments,
    create_fixture_for_attribute,
)
from .converter.imports import add_pytest_import, remove_unittest_importfrom, remove_unittest_import
from .converter.cleanup import extract_relevant_cleanup, references_attribute
from .converter.with_helpers import convert_assert_raises_with
from .converter.fixture_builders import build_fixtures_from_setup_assignments
from .converter.params import get_fixture_param_names, make_fixture_params
from .converter.params import append_fixture_params
from .converter.autouse import build_attach_to_instance_fixture, insert_attach_fixture_into_module
from .converter.placement import insert_fixtures_into_module
from .converter.call_utils import is_self_call
from .converter.method_patterns import (
    normalize_method_name as _normalize_method_name,
    is_setup_method as _is_setup_method_helper,
    is_teardown_method as _is_teardown_method_helper,
    is_test_method as _is_test_method_helper,
)
from .converter.class_checks import is_unittest_testcase_base
from .converter.assertion_dispatch import convert_assertion
from .converter.fixture_body import build_fixture_body
from .converter.fixture_function import create_fixture_function
from .converter.method_params import (
    should_remove_first_param as _should_remove_first_param_helper,
    remove_method_self_references as _remove_method_self_references_helper,
)
from .converter.decorators import build_pytest_fixture_decorator


class UnittestToPytestTransformer(cst.CSTTransformer):
    """Transform unittest-style tests to pytest-style tests."""

    def __init__(self, compat: bool = True) -> None:
        """Initialize the transformer.

        Args:
            compat: If True, emit autouse compatibility fixture to attach fixtures
                to unittest-style test instances (default: True).
        """
        # Deprecation: prefer staged pipeline
        warnings.warn(
            "UnittestToPytestTransformer is deprecated; prefer the staged pipeline (engine='pipeline').",
            DeprecationWarning,
            stacklevel=2,
        )
        self.compat = bool(compat)
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
            result = remove_unittest_importfrom(updated_node)
            if result is cst.RemovalSentinel.REMOVE:
                self.has_unittest_content = True
            return result
        except (AttributeError, TypeError, ValueError):
            return original_node

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.Import | cst.RemovalSentinel:
        """Handle import statements."""
        try:
            result = remove_unittest_import(updated_node)
            if result is cst.RemovalSentinel.REMOVE:
                self.has_unittest_content = True
            return result
        except (AttributeError, TypeError, ValueError):
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
                from .converter.class_checks import remove_unittest_bases

                filtered = remove_unittest_bases(list(updated_node.bases))

                # If no bases remain, create a simple class without inheritance
                if not filtered:
                    updated_node = updated_node.with_changes(bases=[])
                else:
                    updated_node = updated_node.with_changes(bases=filtered)
        except (AttributeError, TypeError, ValueError):
            return original_node

        return updated_node        

    def _should_remove_first_param(self, node: cst.FunctionDef) -> bool:
        """Delegate to helper for first-parameter removal logic."""
        return _should_remove_first_param_helper(node)

    def _remove_method_self_references(self, node: cst.FunctionDef) -> tuple[list[cst.Param], cst.BaseSuite]:
        """Delegate removal to helper to keep transformer thin and testable."""
        new_params, new_body = _remove_method_self_references_helper(node)
        # Ensure returned body is typed as BaseSuite for callers
        return list(new_params), cast(cst.BaseSuite, new_body)

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
                    # Combine existing params (excluding self) with fixture params
                    all_params = append_fixture_params(updated_node.params.with_changes(params=new_params), fixture_params).params
                else:
                    all_params = new_params
                
                return updated_node.with_changes(
                    params=updated_node.params.with_changes(params=all_params),
                    body=new_body,
                )
        except (AttributeError, TypeError, ValueError):
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
        except (AttributeError, TypeError, ValueError):
            return original_node
        
        return updated_node

    def leave_With(
        self, original_node: cst.With, updated_node: cst.With
    ) -> cst.With:
        """Convert unittest assertRaises context managers to pytest.raises."""
        try:
            new_with, needs = convert_assert_raises_with(updated_node)
            if new_with is not None:
                # propagate import requirement to transformer state
                if needs:
                    self.needs_pytest_import = True
                return new_with
        except (AttributeError, TypeError, ValueError):
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

            # Add autouse fixture to attach fixture values to unittest-style test instances
            updated_node = self._add_autouse_instance_attachment_fixture(updated_node)
                
        except (AttributeError, TypeError, ValueError, cst.ParserSyntaxError):
            # If processing fails due to node shape or parse issues, return original node unchanged
            return original_node
        
        return updated_node

    def _is_unittest_testcase(self, base: cst.Arg) -> bool:
        """Delegate to class_checks helper to detect unittest TestCase bases."""
        return is_unittest_testcase_base(base)

    def _normalize_method_name(self, name: str) -> str:
        """Delegate normalization to helper module."""
        return _normalize_method_name(name)

    def _is_setup_method(self, method_name: str) -> bool:
        """Delegate to helper that encapsulates matching rules."""
        return _is_setup_method_helper(method_name, self._setup_patterns)

    def _is_teardown_method(self, method_name: str) -> bool:
        """Delegate to helper that encapsulates matching rules."""
        return _is_teardown_method_helper(method_name, self._teardown_patterns)

    def _is_test_method(self, method_name: str) -> bool:
        """Delegate to helper that encapsulates matching rules."""
        return _is_test_method_helper(method_name, self._test_patterns)

    def _convert_assertion(
        self, method_name: str, args: Sequence[cst.Arg]
    ) -> cst.BaseSmallStatement | None:
        """Delegate assertion conversion to a pure helper."""
        return convert_assertion(method_name, args)

    def _assert_raises(self, args: Sequence[cst.Arg]) -> cst.Call:
        """Convert assertRaises to pytest.raises context manager."""
        # Side-effect: ensure pytest will be imported in the module
        self.needs_pytest_import = True
        return make_pytest_raises_call(args)

    def _assert_raises_regex(self, args: Sequence[cst.Arg]) -> cst.Call:
        """Convert assertRaisesRegex to pytest.raises with match parameter."""
        self.needs_pytest_import = True
        return make_pytest_raises_regex_call(args)

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
        return create_pytest_raises_withitem(method_name, args)

    def _remove_self_references(self, node: cst.CSTNode) -> cst.CSTNode:
        """Remove self/cls references from attribute accesses in fixture bodies."""
        # .visit can return varied CST node types; cast to CSTNode for typing
        return cast(cst.CSTNode, node.visit(SelfReferenceRemover()))

    def _add_pytest_import(self, module_node: cst.Module) -> cst.Module:
        """Delegate to pure helper that adds pytest import to the module.

        Kept as a thin wrapper so transformer instance state can be updated here
        before delegating to the pure function if necessary.
        """
        return add_pytest_import(module_node)

    def _add_autouse_instance_attachment_fixture(self, module_node: cst.Module) -> cst.Module:
        """Add an autouse fixture that attaches created fixtures to unittest-style test instances.

        This fixture is only added when the transformer detected unittest.TestCase usage
        and when fixtures were created from setUp assignments.
        """
        if not self.has_unittest_content or not self.setup_fixtures or not self.compat:
            return module_node

        fixture_func = build_attach_to_instance_fixture(self.setup_fixtures)
        return insert_attach_fixture_into_module(module_node, fixture_func)

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
        # Delegate placement to helper
        return insert_fixtures_into_module(module_node, self.setup_fixtures)

    def _is_self_call(self, call_node: cst.Call) -> tuple[str, Sequence[cst.Arg]] | None:
        """Delegate to pure helper to detect self.method() calls."""
        return is_self_call(call_node)

    def _should_skip_assertion_conversion(self, method_name: str) -> bool:
        """Check if assertion method should be skipped (handled elsewhere)."""
        return method_name in ("assertRaises", "assertRaisesRegex")

    def _convert_self_assertion_to_pytest(
        self, call_node: cst.Call
    ) -> cst.BaseSmallStatement | None:
        """Convert self.assertion() calls to pytest assertions."""
        try:
            # First try to detect self.method(...) calls
            call_info = self._is_self_call(call_node)
            if call_info:
                method_name, args = call_info
                if self._should_skip_assertion_conversion(method_name):
                    return None
                return self._convert_assertion(method_name, args)

            # If SelfReferenceRemover ran earlier, the call may now be assertX(...)
            # where func is a Name. Handle that as a fallback.
            if isinstance(call_node.func, cst.Name):
                method_name = call_node.func.value
                if self._should_skip_assertion_conversion(method_name):
                    return None
                return self._convert_assertion(method_name, call_node.args)
        except (AttributeError, TypeError, ValueError):
            return None
        # Ensure explicit None return when no conversion applied
        return None

    def _parse_setup_assignments(self, node: cst.FunctionDef) -> dict[str, cst.BaseExpression]:
        """Delegate parsing of setUp assignments to a pure helper."""
        return parse_setup_assignments(node)

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
        # Delegate to pure helper which uses teardown_cleanup mapping
        return create_fixture_for_attribute(attr_name, value_expr, self.teardown_cleanup)

    def _get_fixture_params_for_test_method(self) -> list[str]:
        """Get list of fixture names that should be parameters for test methods."""
        return get_fixture_param_names(self.setup_fixtures)

    def _add_fixture_params_to_test_method(
        self, existing_params: cst.Parameters, fixture_names: list[str]
    ) -> cst.Parameters:
        """Add fixture parameters to test method signature."""
        # Delegate to pure helper that builds a Parameters object for fixtures
        return make_fixture_params(existing_params, fixture_names)

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
            from .converter.teardown_helpers import associate_cleanup_with_fixtures

            associate_cleanup_with_fixtures(self.teardown_cleanup, self.setup_fixtures.keys(), cleanup_statements)
        
        # Remove the original tearDown method
        return cst.RemovalSentinel.REMOVE
    
    def _create_fixtures_with_cleanup(self, cleanup_statements: list[Any]) -> None:
        """Create fixtures from setup assignments with tearDown cleanup integration."""
        fixtures, needs = build_fixtures_from_setup_assignments(self.setup_assignments, self.teardown_cleanup)
        # Merge into transformer fixtures mapping
        self.setup_fixtures.update(fixtures)
        if needs:
            self.needs_pytest_import = True
    
    def _extract_relevant_cleanup(self, cleanup_statements: list[Any], attr_name: str) -> list[Any]:
        """Delegate to pure helper that extracts cleanup statements referencing attr_name."""
        return extract_relevant_cleanup(cleanup_statements, attr_name)
    
    def _references_attribute(self, expr: Any, attr_name: str) -> bool:
        """Delegate to pure helper that checks for attribute references."""
        return references_attribute(expr, attr_name)
    
    def _create_fixture_with_cleanup(self, attr_name: str, value_expr: cst.BaseExpression, cleanup_statements: list[cst.BaseStatement]) -> cst.FunctionDef:
        """Create a fixture with yield pattern and cleanup."""
        # Create the @pytest.fixture decorator
        fixture_decorator = build_pytest_fixture_decorator()
        # Build the fixture body (literal-yield vs. bound-value + safe cleanup)
        body = build_fixture_body(attr_name, value_expr, cleanup_statements)

        # Create the fixture function using extracted helper
        return create_fixture_function(attr_name, body, fixture_decorator)
    
    def _create_simple_fixture(self, attr_name: str, value_expr: cst.BaseExpression) -> cst.FunctionDef:
        """Create a simple fixture with return (no cleanup needed)."""
        # Delegate to extracted helper to keep method thin for easier testing
        self.needs_pytest_import = True
        return create_simple_fixture(attr_name, value_expr)