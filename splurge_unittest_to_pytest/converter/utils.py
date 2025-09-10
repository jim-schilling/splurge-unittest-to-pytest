"""Utility helpers extracted from the large converter module.

Start with small, well-tested helpers and move more pieces here iteratively.
"""
from __future__ import annotations


import libcst as cst


class SelfReferenceRemover(cst.CSTTransformer):
    """Remove self/cls references from attribute accesses."""

    def __init__(self, param_names: set[str] | None = None) -> None:
        self.param_names = param_names or {"self", "cls"}

    def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.Attribute | cst.Name:
        if isinstance(updated_node.value, cst.Name) and updated_node.value.value in self.param_names:
            return updated_node.attr
        return updated_node


def normalize_method_name(name: str) -> str:
    """Normalize method name for pattern matching (convert camelCase to snake_case)."""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
