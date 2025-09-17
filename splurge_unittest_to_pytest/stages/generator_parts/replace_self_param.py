from __future__ import annotations

import libcst as cst
from typing import Set

DOMAINS = ["generator"]


# Associated domains for this module


class ReplaceSelfWithParam(cst.CSTTransformer):
    """Transformer that replaces ``self.attr``/``cls.attr`` with a Name.

    When an attribute matches the provided reference set, returns a Name
    node for the attribute so self-references become parameter references
    for generated fixtures.
    """

    def __init__(self, refs_set: Set[str]) -> None:
        self.refs = refs_set

    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
        if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
            if isinstance(original.attr, cst.Name) and original.attr.value in self.refs:
                return cst.Name(original.attr.value)
        return updated
