"""Helpers for building fixtures and sanitizing cleanup statements."""

from __future__ import annotations

from typing import List, cast

import libcst as cst


def replace_attr_references_in_statements(
    statements: List[cst.BaseStatement], attr_name: str, value_name: str
) -> List[cst.BaseStatement]:
    """Replace references to an attribute (e.g. self.attr or bare `attr`) with a local value name.

    This mirrors the in-place ReplaceName transformer previously nested inside
    `converter._create_fixture_with_cleanup` so the behavior is testable.
    """
    class ReplaceName(cst.CSTTransformer):
        def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
            if original_node.value == attr_name:
                return cst.Name(value_name)
            return updated_node

        def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.BaseExpression:
            if (
                isinstance(updated_node.value, cst.Name)
                and updated_node.attr.value == attr_name
                and updated_node.value.value in {"self", "cls"}
            ):
                return cst.Name(value_name)
            return updated_node

    replacer = ReplaceName()
    safe: List[cst.BaseStatement] = []
    for stmt in statements:
        replaced = stmt.visit(replacer)
        safe.append(cast(cst.BaseStatement, replaced))

    return safe
