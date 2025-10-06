"""Property-based tests for assert transformer functionality.

This module contains Hypothesis-based property tests for the assert
transformation functions in splurge_unittest_to_pytest.transformers.assert_transformer.
These tests verify that transformations preserve semantic meaning, produce
valid AST nodes, and behave conservatively when transformation is not possible.
"""

import ast
import unittest
from typing import Any

import hypothesis as hyp
import libcst as cst
import pytest
from hypothesis import given, settings

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    transform_assert_almost_equal,
    transform_assert_equal,
    transform_assert_false,
    transform_assert_greater,
    transform_assert_greater_equal,
    transform_assert_in,
    transform_assert_is,
    transform_assert_is_none,
    transform_assert_is_not,
    transform_assert_is_not_none,
    transform_assert_isinstance,
    transform_assert_less,
    transform_assert_less_equal,
    transform_assert_not_equal,
    transform_assert_not_in,
    transform_assert_not_isinstance,
    transform_assert_true,
)
from tests.hypothesis_config import DEFAULT_SETTINGS
from tests.property.strategies import (
    cst_call_args,
    cst_expressions,
    migration_configs,
    unittest_assertion_calls,
)


class TestAssertTransformerProperties:
    """Property-based tests for assert transformation functions."""

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_transformations_preserve_ast_validity(self, call_node: cst.Call) -> None:
        """Test that all transformation functions produce valid AST nodes."""
        transformations = [
            transform_assert_equal,
            transform_assert_not_equal,
            transform_assert_true,
            transform_assert_false,
            transform_assert_is,
            transform_assert_is_not,
            transform_assert_is_none,
            transform_assert_is_not_none,
            transform_assert_in,
            transform_assert_not_in,
            transform_assert_isinstance,
            transform_assert_not_isinstance,
            transform_assert_greater,
            transform_assert_greater_equal,
            transform_assert_less,
            transform_assert_less_equal,
        ]

        for transform_func in transformations:
            result = transform_func(call_node)
            # Result should be either the original node or a valid CST node
            assert isinstance(result, cst.CSTNode | type(call_node))

            # If it's an Assert node, it should have a test attribute
            if isinstance(result, cst.Assert):
                assert hasattr(result, "test")
                assert result.test is not None

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_transformations_are_conservative(self, call_node: cst.Call) -> None:
        """Test that transformations return original node when they cannot transform."""
        # For calls with insufficient arguments, transformations should return original
        if len(call_node.args) < 1:
            assert transform_assert_true(call_node) is call_node
            assert transform_assert_false(call_node) is call_node

        if len(call_node.args) < 2:
            assert transform_assert_equal(call_node) is call_node
            assert transform_assert_not_equal(call_node) is call_node
            assert transform_assert_is(call_node) is call_node
            assert transform_assert_is_not(call_node) is call_node
            assert transform_assert_greater(call_node) is call_node
            assert transform_assert_greater_equal(call_node) is call_node
            assert transform_assert_less(call_node) is call_node
            assert transform_assert_less_equal(call_node) is call_node
            assert transform_assert_in(call_node) is call_node
            assert transform_assert_not_in(call_node) is call_node

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_assert_equal_transformation_correctness(self, call_node: cst.Call) -> None:
        """Test that assertEqual transforms to equivalent assert statement."""
        if len(call_node.args) >= 2:
            result = transform_assert_equal(call_node)
            if isinstance(result, cst.Assert):
                # Should be a comparison with == operator
                assert isinstance(result.test, cst.Comparison)
                assert len(result.test.comparisons) == 1
                assert isinstance(result.test.comparisons[0].operator, cst.Equal)

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_assert_not_equal_transformation_correctness(self, call_node: cst.Call) -> None:
        """Test that assertNotEqual transforms to equivalent assert statement."""
        if len(call_node.args) >= 2:
            result = transform_assert_not_equal(call_node)
            if isinstance(result, cst.Assert):
                # Should be a comparison with != operator
                assert isinstance(result.test, cst.Comparison)
                assert len(result.test.comparisons) == 1
                assert isinstance(result.test.comparisons[0].operator, cst.NotEqual)

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_assert_true_false_transformation_correctness(self, call_node: cst.Call) -> None:
        """Test that assertTrue/assertFalse transform correctly."""
        if len(call_node.args) >= 1:
            true_result = transform_assert_true(call_node)
            false_result = transform_assert_false(call_node)

            if isinstance(true_result, cst.Assert):
                # assertTrue should directly assert the expression
                assert true_result.test == call_node.args[0].value

            if isinstance(false_result, cst.Assert):
                # assertFalse should assert the negation
                assert isinstance(false_result.test, cst.UnaryOperation)
                assert isinstance(false_result.test.operator, cst.Not)

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_assert_is_is_not_transformation_correctness(self, call_node: cst.Call) -> None:
        """Test that assertIs/assertIsNot transform to is/is not operators."""
        if len(call_node.args) >= 2:
            is_result = transform_assert_is(call_node)
            is_not_result = transform_assert_is_not(call_node)

            if isinstance(is_result, cst.Assert):
                assert isinstance(is_result.test, cst.Comparison)
                assert len(is_result.test.comparisons) == 1
                assert isinstance(is_result.test.comparisons[0].operator, cst.Is)

            if isinstance(is_not_result, cst.Assert):
                assert isinstance(is_not_result.test, cst.Comparison)
                assert len(is_not_result.test.comparisons) == 1
                assert isinstance(is_not_result.test.comparisons[0].operator, cst.IsNot)

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_assert_none_transformation_correctness(self, call_node: cst.Call) -> None:
        """Test that assertIsNone/assertIsNotNone transform correctly."""
        if len(call_node.args) >= 1:
            is_none_result = transform_assert_is_none(call_node)
            is_not_none_result = transform_assert_is_not_none(call_node)

            if isinstance(is_none_result, cst.Assert):
                assert isinstance(is_none_result.test, cst.Comparison)
                assert len(is_none_result.test.comparisons) == 1
                assert isinstance(is_none_result.test.comparisons[0].operator, cst.Is)
                assert isinstance(is_none_result.test.comparisons[0].comparator, cst.Name)
                assert is_none_result.test.comparisons[0].comparator.value == "None"

            if isinstance(is_not_none_result, cst.Assert):
                assert isinstance(is_not_none_result.test, cst.Comparison)
                assert len(is_not_none_result.test.comparisons) == 1
                assert isinstance(is_not_none_result.test.comparisons[0].operator, cst.IsNot)
                assert isinstance(is_not_none_result.test.comparisons[0].comparator, cst.Name)
                assert is_not_none_result.test.comparisons[0].comparator.value == "None"

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_assert_in_not_in_transformation_correctness(self, call_node: cst.Call) -> None:
        """Test that assertIn/assertNotIn transform to in/not in operators."""
        if len(call_node.args) >= 2:
            in_result = transform_assert_in(call_node)
            not_in_result = transform_assert_not_in(call_node)

            if isinstance(in_result, cst.Assert):
                assert isinstance(in_result.test, cst.Comparison)
                assert len(in_result.test.comparisons) == 1
                assert isinstance(in_result.test.comparisons[0].operator, cst.In)

            if isinstance(not_in_result, cst.Assert):
                assert isinstance(not_in_result.test, cst.Comparison)
                assert len(not_in_result.test.comparisons) == 1
                assert isinstance(not_in_result.test.comparisons[0].operator, cst.NotIn)

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_assert_isinstance_transformation_correctness(self, call_node: cst.Call) -> None:
        """Test that assertIsInstance/assertNotIsInstance transform correctly."""
        if len(call_node.args) >= 2:
            isinstance_result = transform_assert_isinstance(call_node)
            not_isinstance_result = transform_assert_not_isinstance(call_node)

            if isinstance(isinstance_result, cst.Assert):
                # Should be an isinstance() call
                assert isinstance(isinstance_result.test, cst.Call)
                assert isinstance(isinstance_result.test.func, cst.Name)
                assert isinstance_result.test.func.value == "isinstance"

            if isinstance(not_isinstance_result, cst.Assert):
                # Should be a negated isinstance() call
                assert isinstance(not_isinstance_result.test, cst.UnaryOperation)
                assert isinstance(not_isinstance_result.test.operator, cst.Not)
                assert isinstance(not_isinstance_result.test.expression, cst.Call)
                assert isinstance(not_isinstance_result.test.expression.func, cst.Name)
                assert not_isinstance_result.test.expression.func.value == "isinstance"

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_comparison_assertions_transformation_correctness(self, call_node: cst.Call) -> None:
        """Test that comparison assertions transform to correct operators."""
        if len(call_node.args) >= 2:
            greater_result = transform_assert_greater(call_node)
            greater_equal_result = transform_assert_greater_equal(call_node)
            less_result = transform_assert_less(call_node)
            less_equal_result = transform_assert_less_equal(call_node)

            if isinstance(greater_result, cst.Assert):
                assert isinstance(greater_result.test, cst.Comparison)
                assert len(greater_result.test.comparisons) == 1
                assert isinstance(greater_result.test.comparisons[0].operator, cst.GreaterThan)

            if isinstance(greater_equal_result, cst.Assert):
                assert isinstance(greater_equal_result.test, cst.Comparison)
                assert len(greater_equal_result.test.comparisons) == 1
                assert isinstance(greater_equal_result.test.comparisons[0].operator, cst.GreaterThanEqual)

            if isinstance(less_result, cst.Assert):
                assert isinstance(less_result.test, cst.Comparison)
                assert len(less_result.test.comparisons) == 1
                assert isinstance(less_result.test.comparisons[0].operator, cst.LessThan)

            if isinstance(less_equal_result, cst.Assert):
                assert isinstance(less_equal_result.test, cst.Comparison)
                assert len(less_equal_result.test.comparisons) == 1
                assert isinstance(less_equal_result.test.comparisons[0].operator, cst.LessThanEqual)

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls(), config=migration_configs())
    def test_assert_almost_equal_with_config(self, call_node: cst.Call, config: dict[str, Any]) -> None:
        """Test that assertAlmostEqual works with configuration."""
        if len(call_node.args) >= 2:
            result = transform_assert_almost_equal(call_node, config)
            # Should either transform or return original
            assert isinstance(result, cst.CSTNode | type(call_node))

    @DEFAULT_SETTINGS
    @given(call_node=unittest_assertion_calls())
    def test_transformations_preserve_argument_structure(self, call_node: cst.Call) -> None:
        """Test that transformations preserve the structure of arguments."""
        transformations = [
            transform_assert_equal,
            transform_assert_not_equal,
            transform_assert_true,
            transform_assert_false,
            transform_assert_is,
            transform_assert_is_not,
            transform_assert_is_none,
            transform_assert_is_not_none,
            transform_assert_in,
            transform_assert_not_in,
            transform_assert_greater,
            transform_assert_greater_equal,
            transform_assert_less,
            transform_assert_less_equal,
        ]

        for transform_func in transformations:
            result = transform_func(call_node)
            if isinstance(result, cst.Assert) and len(call_node.args) >= 1:
                # The first argument should be preserved in the test expression
                if hasattr(result.test, "left"):
                    # For comparisons, left side should relate to first arg
                    assert result.test.left == call_node.args[0].value
                elif result.test == call_node.args[0].value:
                    # For simple assertions like assertTrue
                    pass
