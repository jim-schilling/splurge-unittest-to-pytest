"""Helpers to collect self/attribute dependencies from fixture bodies.

This module contains a small public API used by the generator stage to
inspect function bodies and collect attributes referenced on ``self`` or
module-level fixtures. Kept minimal and pure so it can be tested in
isolation.
"""

from __future__ import annotations

from typing import Set

import libcst as cst


def collect_self_attributes(node: cst.CSTNode) -> Set[str]:
    """Return the set of attribute names accessed via ``self`` or ``cls`` in
    the provided node. The node can be a Module, a BaseExpression, or any
    other libcst node; this helper will traverse it and collect simple
    attribute accesses like ``self.name``.

    Args:
        node: A libcst node to inspect.

    Returns:
        A set of attribute names accessed as ``self.<name>`` or ``cls.<name>``.
    """

    class _Visitor(cst.CSTVisitor):
        def __init__(self) -> None:
            self.attrs: Set[str] = set()

        def visit_Attribute(self, node: cst.Attribute) -> None:
            value = node.value
            if isinstance(value, cst.Name) and value.value in ("self", "cls"):
                attr = node.attr
                if isinstance(attr, cst.Name):
                    self.attrs.add(attr.value)

    v = _Visitor()
    # Some nodes (like BaseExpression) support visit; Module and other nodes do too.
    node.visit(v)
    return v.attrs
