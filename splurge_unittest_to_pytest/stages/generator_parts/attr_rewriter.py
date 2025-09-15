from __future__ import annotations


import libcst as cst

DOMAINS = ["generator", "rewriter"]


# Associated domains for this module


class AttrRewriter(cst.CSTTransformer):
    """Transformer that replaces attributes of the form ``self.attr`` or
    ``cls.attr`` with a bare ``Name`` using either the fixture name or a
    provided local name.

    This encapsulates the small visitor class previously embedded inline in
    `stages/generator.py` so it can be unit tested independently.
    """

    def __init__(self, target_attr: str, local: str) -> None:
        self.target_attr = target_attr
        self.local = local

    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
        if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
            if isinstance(original.attr, cst.Name) and original.attr.value == self.target_attr:
                return cst.Name(self.local)
        return updated


def replace_in_node(
    node: cst.CSTNode, target_attr: str, local: str
) -> cst.CSTNode | cst.RemovalSentinel | cst.FlattenSentinel[cst.CSTNode]:
    """Apply AttrRewriter to a CST node and return the rewritten node."""
    return node.visit(AttrRewriter(target_attr, local))
