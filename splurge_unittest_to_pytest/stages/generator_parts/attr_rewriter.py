"""Helpers to rewrite attribute access to local names.

This module contains a small libcst transformer used in generator
tests to replace attribute expressions like ``self.attr`` or ``cls.attr``
with a plain :class:`libcst.Name` node when the attribute name matches
the configured target.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations


import libcst as cst

DOMAINS = ["generator", "rewriter"]


# Associated domains for this module


class AttrRewriter(cst.CSTTransformer):
    """Transformer to replace ``self.attr`` or ``cls.attr`` with a Name.

    When the attribute base is ``self`` or ``cls`` and the attribute name
    matches the configured target, this transformer returns a plain
    :class:`libcst.Name` node with the provided local identifier.
    """

    def __init__(
        self,
        target_attr: str,
        local: str,
    ) -> None:
        self.target_attr = target_attr
        self.local = local

    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
        if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
            if isinstance(original.attr, cst.Name) and original.attr.value == self.target_attr:
                return cst.Name(self.local)
        return updated


def replace_in_node(
    node: cst.CSTNode,
    target_attr: str,
    local: str,
) -> cst.CSTNode | cst.RemovalSentinel | cst.FlattenSentinel[cst.CSTNode]:
    """Apply AttrRewriter to ``node`` and return the rewritten node.

    This helper visits the node with AttrRewriter(target_attr, local).
    """
    return node.visit(AttrRewriter(target_attr, local))
