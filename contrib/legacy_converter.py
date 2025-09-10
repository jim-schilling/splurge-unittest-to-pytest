"""Archived legacy converter implementation.

This file contains the historical UnittestToPytestTransformer implementation
from the original public API. It has been moved out of the package proper and
archived here to avoid being imported by default. Keep for reference or
advanced users who need the legacy behavior.
"""

import warnings

import libcst as cst


class SelfReferenceRemover(cst.CSTTransformer):
    """Remove self/cls references from attribute accesses."""
    
    def __init__(self, param_names: set[str] | None = None):
        self.param_names = param_names or {"self", "cls"}

    def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.Attribute | cst.Name:
        if (isinstance(updated_node.value, cst.Name) and 
            updated_node.value.value in self.param_names):
            return updated_node.attr
        return updated_node


class UnittestToPytestTransformer(cst.CSTTransformer):
    """Transform unittest-style tests to pytest-style tests.

    Archived here. Prefer the staged pipeline (`engine='pipeline'`) for
    current conversions.
    """

    def __init__(self, compat: bool = True) -> None:
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
        self.setup_fixtures: dict[str, cst.FunctionDef] = {}
        self.teardown_cleanup: dict[str, list[cst.BaseStatement]] = {}
        self.setup_assignments: dict[str, cst.BaseExpression] = {}
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

    # NOTE: implementation intentionally truncated in archive; see original
    # history for the full implementation if needed.
