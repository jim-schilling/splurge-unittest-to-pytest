"""Small libcst transformers used by the generator stage.

These transformers are intentionally minimal: they perform narrow,
well-specified rewrites (replace `self.name` with `name`, replace
attribute access with a local name, etc.). Keeping them separate makes
testing and reasoning simpler.
"""

from __future__ import annotations


import libcst as cst

DOMAINS = ["generator", "transform"]

# Associated domains for this module


class ReplaceSelfWithName(cst.CSTTransformer):
    """Replace occurrences of ``self.<attr>`` with the bare ``<attr>`` name.

    Only replaces simple attribute accesses where the attribute is a Name.
    """

    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
        # Walk the ORIGINAL node to determine whether this Attribute
        # expression is part of an attribute chain rooted at `self`.
        # We examine the original tree (not the updated one) so that
        # an outer attribute can still be recognized even if inner
        # attributes were already rewritten.
        node: cst.BaseExpression = original
        while isinstance(node, cst.Attribute):
            node = node.value
        if isinstance(node, cst.Name) and node.value == "self":
            attr = original.attr
            if isinstance(attr, cst.Name):
                # Replace the whole chain with the right-most attribute name.
                return cst.Name(attr.value)
        return updated


class ReplaceAttrWithLocal(cst.CSTTransformer):
    """Replace attribute accesses like ``obj.attr`` with a provided local name.

    Usage: instantiate with mapping {'obj': 'local_name'} and any Attribute whose
    value is a Name matching a key will be replaced with the mapped local Name.
    """

    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
        value = updated.value
        if isinstance(value, cst.Name) and value.value in self._mapping:
            attr = updated.attr
            if isinstance(attr, cst.Name):
                # produce the mapped local name (we keep the attribute name to avoid collisions)
                return cst.Name(self._mapping[value.value] + "__" + attr.value)
        return updated


class ReplaceSelf(cst.CSTTransformer):
    """Replace ``self`` name occurrences with an alternative name.

    Useful for rewriting test fixtures that reference ``self`` when emitting
    top-level fixtures.
    """

    def __init__(self, replacement: str) -> None:
        self._replacement = replacement

    def leave_Name(self, original: cst.Name, updated: cst.Name) -> cst.BaseExpression:
        if original.value == "self":
            return cst.Name(self._replacement)
        return updated


class ReplaceNameWithLocal(cst.CSTTransformer):
    """Replace occurrences of a given name with a provided local name.

    Example: replace Name('x') -> Name('_x_value'). Used when rewriting
    cleanup code to reference generated locals.
    """

    def __init__(self, original: str, replacement: str) -> None:
        self._original = original
        self._replacement = replacement

    def leave_Name(self, original: cst.Name, updated: cst.Name) -> cst.BaseExpression:
        if original.value == self._original:
            return cst.Name(self._replacement)
        return updated
