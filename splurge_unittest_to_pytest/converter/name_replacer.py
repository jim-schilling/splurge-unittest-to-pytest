"""Name replacer: replace Name/Attribute occurrences in libcst nodes.

Provides a :class:`NameReplacer` transformer which rewrites occurrences
of a named attribute (including ``self.attr`` or ``cls.attr``) to a
provided value name. The helper :func:`replace_names_in_statements` applies
the transform to an iterable of statements and returns the rewritten list.

Publics:
    NameReplacer: A CSTTransformer to replace name/attribute occurrences.
    replace_names_in_statements: Apply the transformer to statements.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Iterable, cast

import libcst as cst

DOMAINS = ["converter", "naming"]

# Associated domains for this module


class NameReplacer(cst.CSTTransformer):
    def __init__(self, attr_name: str, value_name: str) -> None:
        super().__init__()
        self.attr_name = attr_name
        self.value_name = value_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if original_node.value == self.attr_name:
            return cst.Name(self.value_name)
        return updated_node

    def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.BaseExpression:
        # If attribute like self.attr_name or cls.attr_name => replace with value_name
        if (
            isinstance(updated_node.value, cst.Name)
            and updated_node.attr.value == self.attr_name
            and updated_node.value.value in {"self", "cls"}
        ):
            return cst.Name(self.value_name)
        return updated_node


def replace_names_in_statements(
    statements: Iterable[cst.BaseStatement], attr_name: str, value_name: str
) -> list[cst.BaseStatement]:
    replacer = NameReplacer(attr_name, value_name)
    return [cast(cst.BaseStatement, stmt.visit(replacer)) for stmt in statements]
