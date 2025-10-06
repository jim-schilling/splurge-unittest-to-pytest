"""
Base property tests for splurge-unittest-to-pytest.

This module contains fundamental properties that should hold true for all
transformations and components in the library.
"""

import ast

import libcst as cst
import pytest
from hypothesis import given, settings

from tests.hypothesis_config import DEFAULT_SETTINGS
from tests.property.strategies import (
    migration_configs,
    python_source_code,
    unittest_assertion_calls,
)


class TestBaseProperties:
    """Fundamental properties that should hold for all transformations."""

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_all_generated_code_is_valid_python(self, source_code: str) -> None:
        """All generated Python source code should be syntactically valid."""
        try:
            ast.parse(source_code)
        except SyntaxError as e:
            pytest.fail(f"Generated code is not valid Python: {e}\nCode: {source_code}")

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_assertion_call_nodes_are_well_formed(self, call_node: cst.Call) -> None:
        """Generated assertion call nodes should be well-formed libcst nodes."""
        # Verify the node has the expected structure
        assert isinstance(call_node, cst.Call)
        assert isinstance(call_node.func, cst.Attribute)
        assert isinstance(call_node.func.value, cst.Name)
        assert call_node.func.value.value == "self"
        assert isinstance(call_node.func.attr, cst.Name)

        # Should have some arguments (though possibly empty)
        assert isinstance(call_node.args, list)

    def test_hypothesis_settings_are_loaded(self) -> None:
        """Verify that Hypothesis configuration is properly loaded."""
        # This test ensures our configuration is working
        from hypothesis import settings

        # Check that we can access the loaded profile
        current_settings = settings._current_profile
        assert current_settings is not None

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_libcst_can_parse_generated_code(self, source_code: str) -> None:
        """libcst should be able to parse all generated Python code."""
        try:
            cst.parse_module(source_code)
        except Exception as e:
            pytest.fail(f"libcst failed to parse generated code: {e}\nCode: {source_code}")

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_assertion_methods_exist_in_unittest(self, call_node: cst.Call) -> None:
        """Generated assertion method names should exist in unittest.TestCase."""
        import unittest

        method_name = call_node.func.attr.value
        # Check that the method exists on TestCase
        assert hasattr(unittest.TestCase, method_name), f"Method {method_name} not found on unittest.TestCase"

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_code_length_is_reasonable(self, source_code: str) -> None:
        """Generated code should not be excessively long."""
        # Prevent generation of unreasonably large code snippets
        assert len(source_code) <= 10000, f"Generated code too long: {len(source_code)} characters"

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_call_arguments_are_properly_typed(self, call_node: cst.Call) -> None:
        """Call arguments should be proper libcst Arg nodes."""
        for arg in call_node.args:
            assert isinstance(arg, cst.Arg), f"Expected cst.Arg, got {type(arg)}"
            # Value should be some kind of expression
            assert isinstance(arg.value, cst.BaseExpression), f"Expected expression, got {type(arg.value)}"

    @DEFAULT_SETTINGS
    @given(config=migration_configs())
    def test_migration_configs_are_dicts(self, config: dict) -> None:
        """Generated migration configs should be dictionaries."""
        assert isinstance(config, dict)
        # Should have some expected keys
        expected_keys = {"line_length", "dry_run", "transform_assertions"}
        assert any(key in config for key in expected_keys)
