"""Utilities for analyzing and transforming function and method parameters.

This module provides helpers to decide whether the leading ``self`` or
``cls`` parameter should be removed, and to construct or rewrite
parameter lists when converting instance methods into top-level
functions that accept fixtures.

Publics:
    should_remove_first_param, is_staticmethod, is_classmethod,
    first_param_name, remove_method_self_references

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations


import libcst as cst

from .helpers import SelfReferenceRemover

DOMAINS = ["converter", "parameters"]

# Associated domains for this module


def should_remove_first_param(node: cst.FunctionDef) -> bool:
    """Return True when the first parameter (self/cls) should be removed.

    Logic mirrors transformer._should_remove_first_param.
    """
    if not node.params.params:
        return False

    first_param = node.params.params[0]
    first_param_name = first_param.name.value if hasattr(first_param, "name") else ""

    has_classmethod = any(
        (
            isinstance(decorator, cst.Decorator)
            and isinstance(decorator.decorator, cst.Name)
            and decorator.decorator.value == "classmethod"
        )
        for decorator in (node.decorators or [])
    )

    has_staticmethod = any(
        (
            isinstance(decorator, cst.Decorator)
            and isinstance(decorator.decorator, cst.Name)
            and decorator.decorator.value == "staticmethod"
        )
        for decorator in (node.decorators or [])
    )

    if has_staticmethod:
        return False
    if has_classmethod:
        return first_param_name == "cls"
    return first_param_name == "self"


def is_staticmethod(node: cst.FunctionDef) -> bool:
    """Return True when the function is decorated with @staticmethod."""
    return any(
        (
            isinstance(decorator, cst.Decorator)
            and isinstance(decorator.decorator, cst.Name)
            and decorator.decorator.value == "staticmethod"
        )
        for decorator in (node.decorators or [])
    )


def is_classmethod(node: cst.FunctionDef) -> bool:
    """Return True when the function is decorated with @classmethod."""
    return any(
        (
            isinstance(decorator, cst.Decorator)
            and isinstance(decorator.decorator, cst.Name)
            and decorator.decorator.value == "classmethod"
        )
        for decorator in (node.decorators or [])
    )


def first_param_name(node: cst.FunctionDef) -> str | None:
    """Return the name of the first parameter if present, otherwise None."""
    if not node.params.params:
        return None
    first_param = node.params.params[0]
    return first_param.name.value if hasattr(first_param, "name") else None


def remove_method_self_references(node: cst.FunctionDef) -> tuple[list[cst.Param], cst.BaseSuite]:
    """Remove the first parameter (if applicable) and self/cls references from the body.

    Returns the new parameter list and transformed body.
    """
    new_params = list(node.params.params)
    new_body = node.body

    if should_remove_first_param(node):
        first_param = node.params.params[0]
        param_name = first_param.name.value if hasattr(first_param, "name") else ""
        new_params = new_params[1:]
        remover = SelfReferenceRemover({param_name})
        visited = node.body.visit(remover)
        # The visitor may return sentinel objects (RemovalSentinel/FlattenSentinel).
        # If that happens, fall back to the original body to keep the function valid.
        if isinstance(visited, cst.BaseSuite):
            new_body = visited
        else:
            new_body = node.body

    return new_params, new_body
