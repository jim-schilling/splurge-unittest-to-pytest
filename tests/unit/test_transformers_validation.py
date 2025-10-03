"""Tests for CST validation utilities."""

import libcst as cst
import pytest

from splurge_unittest_to_pytest.transformers.validation import (
    CSTValidationError,
    is_valid_expression,
    safe_get_attribute,
    validate_attribute_chain,
    validate_call_node,
    validate_class_def,
    validate_expression,
    validate_function_def,
    validate_has_body,
    validate_simple_statement,
)


class TestCSTValidationError:
    """Test CSTValidationError class."""

    def test_error_creation(self):
        """Test basic error creation."""
        error = CSTValidationError("Test message")
        assert str(error) == "Test message"
        assert error.node is None

    def test_error_with_node(self):
        """Test error creation with node."""
        node = cst.Name("test")
        error = CSTValidationError("Test message", node)
        assert str(error) == "Test message"
        assert error.node == node


class TestValidateCallNode:
    """Test validate_call_node function."""

    def test_valid_call_node(self):
        """Test validation of valid Call node."""
        node = cst.Call(func=cst.Name("func"), args=[cst.Arg(cst.Name("arg"))])
        result = validate_call_node(node)
        assert result == node

    def test_invalid_node_type(self):
        """Test validation fails for non-Call node."""
        node = cst.Name("test")
        with pytest.raises(CSTValidationError) as exc_info:
            validate_call_node(node)

        assert "Expected Call node" in str(exc_info.value)
        assert exc_info.value.node == node

    def test_min_args_validation(self):
        """Test minimum arguments validation."""
        # Call with no args, require 1
        node = cst.Call(func=cst.Name("func"), args=[])
        with pytest.raises(CSTValidationError) as exc_info:
            validate_call_node(node, min_args=1)

        assert "requires at least 1 arguments" in str(exc_info.value)

    def test_max_args_validation(self):
        """Test maximum arguments validation."""
        # Call with 3 args, max 2
        args = [cst.Arg(cst.Name(f"arg{i}")) for i in range(3)]
        node = cst.Call(func=cst.Name("func"), args=args)
        with pytest.raises(CSTValidationError) as exc_info:
            validate_call_node(node, max_args=2)

        assert "accepts at most 2 arguments" in str(exc_info.value)

    def test_args_in_range(self):
        """Test arguments within valid range."""
        args = [cst.Arg(cst.Name(f"arg{i}")) for i in range(2)]
        node = cst.Call(func=cst.Name("func"), args=args)

        # Should pass with min=1, max=3
        result = validate_call_node(node, min_args=1, max_args=3)
        assert result == node


class TestValidateAttributeChain:
    """Test validate_attribute_chain function."""

    def test_simple_name_match(self):
        """Test validation of simple name."""
        node = cst.Name("test")
        assert validate_attribute_chain(node, ["test"]) is True

    def test_simple_name_no_match(self):
        """Test validation fails for simple name mismatch."""
        node = cst.Name("test")
        assert validate_attribute_chain(node, ["other"]) is False

    def test_attribute_chain_match(self):
        """Test validation of attribute chain."""
        # self.assertEqual
        node = cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertEqual"))
        assert validate_attribute_chain(node, ["self", "assertEqual"]) is True

    def test_attribute_chain_no_match(self):
        """Test validation fails for attribute chain mismatch."""
        # self.assertEqual vs expected self.assertTrue
        node = cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertEqual"))
        assert validate_attribute_chain(node, ["self", "assertTrue"]) is False

    def test_deep_attribute_chain(self):
        """Test validation of deep attribute chain."""
        # obj.attr1.attr2
        node = cst.Attribute(value=cst.Attribute(value=cst.Name("obj"), attr=cst.Name("attr1")), attr=cst.Name("attr2"))
        assert validate_attribute_chain(node, ["obj", "attr1", "attr2"]) is True

    def test_malformed_chain(self):
        """Test validation fails for malformed chain."""
        # Number instead of name/attribute
        node = cst.Integer("42")
        with pytest.raises(CSTValidationError) as exc_info:
            validate_attribute_chain(node, ["test"])

        assert "Unexpected node type" in str(exc_info.value)


class TestValidateFunctionDef:
    """Test validate_function_def function."""

    def test_valid_function_def(self):
        """Test validation of valid FunctionDef."""
        node = cst.FunctionDef(
            name=cst.Name("test_func"),
            params=cst.Parameters(),
            body=cst.IndentedBlock([]),
        )
        result = validate_function_def(node)
        assert result == node

    def test_invalid_function_def(self):
        """Test validation fails for non-FunctionDef."""
        node = cst.ClassDef(
            name=cst.Name("TestClass"),
            body=cst.IndentedBlock([]),
        )
        with pytest.raises(CSTValidationError) as exc_info:
            validate_function_def(node)

        assert "Expected FunctionDef node" in str(exc_info.value)


class TestValidateClassDef:
    """Test validate_class_def function."""

    def test_valid_class_def(self):
        """Test validation of valid ClassDef."""
        node = cst.ClassDef(
            name=cst.Name("TestClass"),
            body=cst.IndentedBlock([]),
        )
        result = validate_class_def(node)
        assert result == node

    def test_invalid_class_def(self):
        """Test validation fails for non-ClassDef."""
        node = cst.FunctionDef(
            name=cst.Name("test_func"),
            params=cst.Parameters(),
            body=cst.IndentedBlock([]),
        )
        with pytest.raises(CSTValidationError) as exc_info:
            validate_class_def(node)

        assert "Expected ClassDef node" in str(exc_info.value)


class TestValidateSimpleStatement:
    """Test validate_simple_statement function."""

    def test_valid_simple_statement(self):
        """Test validation of valid SimpleStatementLine."""
        node = cst.SimpleStatementLine(
            body=[cst.Expr(cst.Name("test"))],
        )
        result = validate_simple_statement(node)
        assert result == node

    def test_invalid_simple_statement(self):
        """Test validation fails for non-SimpleStatementLine."""
        node = cst.FunctionDef(
            name=cst.Name("test_func"),
            params=cst.Parameters(),
            body=cst.IndentedBlock([]),
        )
        with pytest.raises(CSTValidationError) as exc_info:
            validate_simple_statement(node)

        assert "Expected SimpleStatementLine node" in str(exc_info.value)


class TestValidateHasBody:
    """Test validate_has_body function."""

    def test_node_with_body(self):
        """Test validation passes for node with body."""
        node = cst.FunctionDef(
            name=cst.Name("test_func"),
            params=cst.Parameters(),
            body=cst.IndentedBlock([]),
        )
        result = validate_has_body(node)
        assert result == node

    def test_node_without_body(self):
        """Test validation fails for node without body."""
        node = cst.Name("test")
        with pytest.raises(CSTValidationError) as exc_info:
            validate_has_body(node)

        assert "has no body attribute" in str(exc_info.value)


class TestSafeGetAttribute:
    """Test safe_get_attribute function."""

    def test_existing_attribute(self):
        """Test getting existing nested attribute."""
        node = cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertEqual"))

        result = safe_get_attribute(node, "attr.value")
        assert result == "assertEqual"

    def test_nonexistent_attribute(self):
        """Test getting nonexistent attribute returns default."""
        node = cst.Name("test")
        result = safe_get_attribute(node, "nonexistent", "default")
        assert result == "default"

    def test_deep_nested_attribute(self):
        """Test getting deep nested attribute."""
        # Create: self.assertEqual.method
        inner_attr = cst.Attribute(
            value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertEqual")), attr=cst.Name("method")
        )

        result = safe_get_attribute(inner_attr, "attr.value")
        assert result == "method"

    def test_invalid_path(self):
        """Test handling of invalid attribute path."""
        node = cst.Name("test")
        result = safe_get_attribute(node, "invalid.path", "default")
        assert result == "default"

    def test_no_default(self):
        """Test behavior without default value."""
        node = cst.Name("test")
        result = safe_get_attribute(node, "nonexistent")
        assert result is None


class TestIsValidExpression:
    """Test is_valid_expression function."""

    def test_valid_expressions(self):
        """Test validation of valid expression types."""
        valid_nodes = [
            cst.Name("test"),
            cst.Attribute(value=cst.Name("obj"), attr=cst.Name("attr")),
            cst.Call(func=cst.Name("func"), args=[]),
            cst.Subscript(value=cst.Name("arr"), slice=[cst.Index(cst.Integer("0"))]),
            cst.BinaryOperation(left=cst.Integer("1"), operator=cst.Add(), right=cst.Integer("2")),
            cst.UnaryOperation(operator=cst.Not(), expression=cst.Name("x")),
            cst.Comparison(
                left=cst.Name("a"), comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Name("b"))]
            ),
            cst.List([]),
            cst.Tuple([]),
            cst.Dict([]),
            cst.Set([cst.Element(cst.Name("x"))]),  # Non-empty set
            cst.SimpleString('"test"'),
            cst.Integer("42"),
            cst.Float("3.14"),
        ]

        for node in valid_nodes:
            assert is_valid_expression(node) is True

    def test_invalid_expressions(self):
        """Test rejection of invalid expression types."""
        invalid_nodes = [
            cst.FunctionDef(name=cst.Name("func"), params=cst.Parameters(), body=cst.IndentedBlock([])),
            cst.ClassDef(name=cst.Name("cls"), body=cst.IndentedBlock([])),
            cst.If(test=cst.Name("x"), body=cst.IndentedBlock([])),
            cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))]),
        ]

        for node in invalid_nodes:
            assert is_valid_expression(node) is False


class TestValidateExpression:
    """Test validate_expression function."""

    def test_valid_expression(self):
        """Test validation of valid expression."""
        node = cst.Name("test")
        result = validate_expression(node)
        assert result == node

    def test_invalid_expression_type(self):
        """Test validation fails for invalid expression type."""
        node = cst.FunctionDef(
            name=cst.Name("func"),
            params=cst.Parameters(),
            body=cst.IndentedBlock([]),
        )
        with pytest.raises(CSTValidationError) as exc_info:
            validate_expression(node, "test context")

        assert "Expected expression in test context" in str(exc_info.value)

    def test_invalid_expression_structure(self):
        """Test validation fails for invalid expression structure."""
        # Test with a node type that's not a valid expression
        node = cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])
        with pytest.raises(CSTValidationError) as exc_info:
            validate_expression(node, "test context")

        assert "Expected expression in test context" in str(exc_info.value)


class TestValidationIntegration:
    """Test validation functions working together."""

    def test_call_validation_pipeline(self):
        """Test a pipeline of validation functions."""
        # Create a call node: self.assertEqual(a, b)
        call_node = cst.Call(
            func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertEqual")),
            args=[
                cst.Arg(cst.Name("a")),
                cst.Arg(cst.Name("b")),
            ],
        )

        # Validate as call
        validated_call = validate_call_node(call_node, min_args=2, max_args=2)
        assert validated_call == call_node

        # Validate function part is an attribute chain
        func_part = validated_call.func
        assert validate_attribute_chain(func_part, ["self", "assertEqual"]) is True

        # Validate arguments are expressions
        for arg in validated_call.args:
            validate_expression(arg.value, "call argument")

    def test_complex_validation_scenario(self):
        """Test complex validation scenario."""
        # Create: self.assertEqual(len(items), 0)
        complex_call = cst.Call(
            func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertEqual")),
            args=[
                cst.Arg(cst.Call(func=cst.Name("len"), args=[cst.Arg(cst.Name("items"))])),
                cst.Arg(cst.Integer("0")),
            ],
        )

        # Should pass all validations
        validated_call = validate_call_node(complex_call, min_args=2)
        assert validated_call == complex_call

        # Check nested call in first argument
        first_arg_call = validated_call.args[0].value
        assert isinstance(first_arg_call, cst.Call)
        validate_call_node(first_arg_call, min_args=1)

        # Check attribute chain
        assert validate_attribute_chain(validated_call.func, ["self", "assertEqual"]) is True


class TestErrorMessages:
    """Test error message quality."""

    def test_descriptive_error_messages(self):
        """Test that error messages are descriptive."""
        # Test various validation failures
        test_cases = [
            (lambda: validate_call_node(cst.Name("test")), "Expected Call node"),
            (lambda: validate_function_def(cst.Name("test")), "Expected FunctionDef node"),
            (lambda: validate_class_def(cst.Name("test")), "Expected ClassDef node"),
            (
                lambda: validate_call_node(cst.Call(func=cst.Name("f"), args=[]), min_args=1),
                "requires at least 1 arguments",
            ),
            (
                lambda: validate_call_node(cst.Call(func=cst.Name("f"), args=[cst.Arg(cst.Name("x"))] * 3), max_args=2),
                "accepts at most 2 arguments",
            ),
        ]

        for validation_func, expected_message in test_cases:
            with pytest.raises(CSTValidationError) as exc_info:
                validation_func()

            assert expected_message in str(exc_info.value)

    def test_error_preserves_node(self):
        """Test that errors preserve the problematic node."""
        node = cst.Name("problematic")
        try:
            validate_call_node(node)
            pytest.fail("Should have raised CSTValidationError")
        except CSTValidationError as e:
            assert e.node == node


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_call_args(self):
        """Test validation of call with no arguments."""
        call_node = cst.Call(func=cst.Name("func"), args=[])
        result = validate_call_node(call_node, min_args=0, max_args=0)
        assert result == call_node

    def test_none_max_args(self):
        """Test validation with None max_args (unlimited)."""
        args = [cst.Arg(cst.Name(f"arg{i}")) for i in range(10)]
        call_node = cst.Call(func=cst.Name("func"), args=args)

        result = validate_call_node(call_node, max_args=None)
        assert result == call_node

    def test_attribute_chain_with_extra_depth(self):
        """Test attribute chain validation with extra nesting."""
        # obj.very.deep.chain
        deep_attr = cst.Attribute(
            value=cst.Attribute(
                value=cst.Attribute(value=cst.Name("obj"), attr=cst.Name("very")), attr=cst.Name("deep")
            ),
            attr=cst.Name("chain"),
        )

        assert validate_attribute_chain(deep_attr, ["obj", "very", "deep", "chain"]) is True
        assert validate_attribute_chain(deep_attr, ["obj", "very", "wrong"]) is False

    def test_safe_get_attribute_complex_path(self):
        """Test safe_get_attribute with complex attribute paths."""
        # Create nested structure
        complex_node = cst.Call(func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("method")), args=[])

        # Test various paths
        assert safe_get_attribute(complex_node, "func.attr.value") == "method"
        assert isinstance(safe_get_attribute(complex_node, "func.value"), cst.Name)
        assert safe_get_attribute(complex_node, "func.value.value") == "self"
        assert safe_get_attribute(complex_node, "args") == complex_node.args
        assert safe_get_attribute(complex_node, "nonexistent") is None
        assert safe_get_attribute(complex_node, "nonexistent", "default") == "default"
