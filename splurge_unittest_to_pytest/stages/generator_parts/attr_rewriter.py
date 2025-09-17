from __future__ import annotations


import libcst as cst

DOMAINS = ["generator", "rewriter"]


# Associated domains for this module


class AttrRewriter(cst.CSTTransformer):
    """Transformer replacing ``self.attr``/``cls.attr`` with a Name.

    Replaces attribute accesses where the value is ``self`` or ``cls`` and
    the attribute matches ``target_attr`` with a plain Name node using the
    provided ``local`` value.
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
    """Apply AttrRewriter to ``node`` and return the rewritten node.

    This helper visits the node with AttrRewriter(target_attr, local).
    """
    return node.visit(AttrRewriter(target_attr, local))
