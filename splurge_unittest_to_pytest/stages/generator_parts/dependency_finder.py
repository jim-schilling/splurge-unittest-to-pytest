"""Helpers to collect self/attribute dependencies from fixture bodies.

Small, testable helpers used by the generator to inspect nodes and collect
attribute names referenced via ``self`` or ``cls``.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Set

import libcst as cst

DOMAINS = ["generator"]

# Associated domains for this module


def collect_self_attributes(node: cst.CSTNode) -> Set[str]:
    """Collect attribute names referenced via ``self`` or ``cls``.

    Args:
        node: A libcst node to inspect.

    Returns:
        A set of attribute names (strings) accessed as ``self.attr`` or
        ``cls.attr`` within the given node.
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
