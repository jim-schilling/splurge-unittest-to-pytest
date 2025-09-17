from __future__ import annotations


import libcst as cst

DOMAINS = ["generator", "rewriter"]


# Associated domains for this module


class AttrRewriter(cst.CSTTransformer):
    """Transformer that replaces ``self.attr`` or ``cls.attr`` with a name.

    The transformer replaces attribute accesses whose value is ``self`` or
    ``cls`` and whose attribute name matches the configured
    ``target_attr``. The attribute is replaced with a plain :class:`libcst.Name`
    whose value is provided via ``local``.

    This class extracts a small visitor previously embedded inline in
    ``stages/generator.py`` so it can be tested in isolation.
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
