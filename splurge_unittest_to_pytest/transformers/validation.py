"""CST node validation utilities for robust transformation.

This module provides validation functions to check CST node structures
before attempting transformations, preventing brittle error handling.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import libcst as cst


class CSTValidationError(ValueError):
    """Raised when CST node validation fails."""

    def __init__(self, message: str, node: cst.CSTNode | None = None):
        self.node = node
        super().__init__(message)


def validate_call_node(node: cst.CSTNode, min_args: int = 0, max_args: int | None = None) -> cst.Call:
    """Validate that a node is a Call with appropriate arguments.

    Args:
        node: The CST node to validate
        min_args: Minimum number of arguments required
        max_args: Maximum number of arguments allowed (None for unlimited)

    Returns:
        The validated Call node

    Raises:
        CSTValidationError: If validation fails
    """
    if not isinstance(node, cst.Call):
        raise CSTValidationError(f"Expected Call node, got {type(node).__name__}", node)

    arg_count = len(node.args)
    if arg_count < min_args:
        raise CSTValidationError(f"Call requires at least {min_args} arguments, got {arg_count}", node)

    if max_args is not None and arg_count > max_args:
        raise CSTValidationError(f"Call accepts at most {max_args} arguments, got {arg_count}", node)

    return node


def validate_attribute_chain(node: cst.CSTNode, expected_chain: Sequence[str]) -> bool:
    """Validate that a node represents the expected attribute chain.

    Args:
        node: The CST node to validate
        expected_chain: Expected attribute names in order (e.g., ['self', 'assertEqual'])

    Returns:
        True if the node matches the expected chain

    Raises:
        CSTValidationError: If the node structure is malformed
    """
    current = node
    for attr_name in reversed(expected_chain):
        if isinstance(current, cst.Name):
            if current.value == attr_name:
                return True
            else:
                return False
        elif isinstance(current, cst.Attribute):
            if current.attr.value != attr_name:
                return False
            current = current.value
        else:
            raise CSTValidationError(f"Unexpected node type in attribute chain: {type(current).__name__}", current)

    return False


def validate_function_def(node: cst.CSTNode) -> cst.FunctionDef:
    """Validate that a node is a FunctionDef.

    Args:
        node: The CST node to validate

    Returns:
        The validated FunctionDef node

    Raises:
        CSTValidationError: If validation fails
    """
    if not isinstance(node, cst.FunctionDef):
        raise CSTValidationError(f"Expected FunctionDef node, got {type(node).__name__}", node)
    return node


def validate_class_def(node: cst.CSTNode) -> cst.ClassDef:
    """Validate that a node is a ClassDef.

    Args:
        node: The CST node to validate

    Returns:
        The validated ClassDef node

    Raises:
        CSTValidationError: If validation fails
    """
    if not isinstance(node, cst.ClassDef):
        raise CSTValidationError(f"Expected ClassDef node, got {type(node).__name__}", node)
    return node


def validate_simple_statement(node: cst.CSTNode) -> cst.SimpleStatementLine:
    """Validate that a node is a SimpleStatementLine.

    Args:
        node: The CST node to validate

    Returns:
        The validated SimpleStatementLine node

    Raises:
        CSTValidationError: If validation fails
    """
    if not isinstance(node, cst.SimpleStatementLine):
        raise CSTValidationError(f"Expected SimpleStatementLine node, got {type(node).__name__}", node)
    return node


def validate_has_body(node: cst.CSTNode) -> cst.CSTNode:
    """Validate that a node has a body attribute.

    Args:
        node: The CST node to validate

    Returns:
        The validated node

    Raises:
        CSTValidationError: If validation fails
    """
    if not hasattr(node, "body"):
        raise CSTValidationError(f"Node {type(node).__name__} has no body attribute", node)
    return node


def safe_get_attribute(node: cst.CSTNode, attr_path: str, default: Any = None) -> Any:
    """Safely get a nested attribute from a CST node.

    Args:
        node: The CST node to access
        attr_path: Dot-separated attribute path (e.g., 'func.value')
        default: Default value if attribute doesn't exist

    Returns:
        The attribute value or default
    """
    try:
        current = node
        for attr in attr_path.split("."):
            if hasattr(current, attr):
                current = getattr(current, attr)
            else:
                return default
        return current
    except (AttributeError, TypeError):
        return default


def is_valid_expression(node: cst.CSTNode) -> bool:
    """Check if a node represents a valid expression.

    Args:
        node: The CST node to check

    Returns:
        True if the node is a valid expression type
    """
    return isinstance(
        node,
        cst.Name
        | cst.Attribute
        | cst.Call
        | cst.Subscript
        | cst.BinaryOperation
        | cst.UnaryOperation
        | cst.Comparison
        | cst.List
        | cst.Tuple
        | cst.Dict
        | cst.Set
        | cst.SimpleString
        | cst.Integer
        | cst.Float,
    )


def validate_expression(node: cst.CSTNode, context: str = "expression") -> cst.BaseExpression:
    """Validate that a node is a valid expression.

    Args:
        node: The CST node to validate
        context: Description of where this validation is happening

    Returns:
        The validated expression node

    Raises:
        CSTValidationError: If validation fails
    """
    if not isinstance(node, cst.BaseExpression):
        raise CSTValidationError(f"Expected expression in {context}, got {type(node).__name__}", node)

    if not is_valid_expression(node):
        raise CSTValidationError(f"Invalid expression type in {context}: {type(node).__name__}", node)

    return node
