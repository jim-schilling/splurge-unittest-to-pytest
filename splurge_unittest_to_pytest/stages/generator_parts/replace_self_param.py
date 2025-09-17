"""Transformer to replace ``self``/``cls`` attribute access with params.

Used by the generator to convert attribute accesses like ``self.x`` into
plain parameter names when the attribute is intended to be provided as a
fixture parameter.
"""

from __future__ import annotations

import libcst as cst
from typing import Set

DOMAINS = ["generator"]


# Associated domains for this module


class ReplaceSelfWithParam(cst.CSTTransformer):
    """Transformer to convert ``self.attr``/``cls.attr`` into parameter names.

    Attributes present in the provided references set are replaced with a
    :class:`libcst.Name` node so that generated fixtures can accept those
    attributes as parameters instead of referencing ``self``/``cls``.
    """

    def __init__(self, refs_set: Set[str]) -> None:
        self.refs = refs_set

    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
        if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
            if isinstance(original.attr, cst.Name) and original.attr.value in self.refs:
                return cst.Name(original.attr.value)
        return updated
