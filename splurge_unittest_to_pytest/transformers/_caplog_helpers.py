"""Caplog helper utilities extracted from assert_transformer.

Provide small pure helpers to detect <alias>.output/records access and
to construct libcst fragments for `caplog.records` and `.getMessage()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import libcst as cst


@dataclass(frozen=True)
class AliasOutputAccess:
    alias_name: str
    slices: tuple[cst.SubscriptElement, ...]


def extract_alias_output_slices(expr: cst.BaseExpression) -> AliasOutputAccess | None:
    """Return alias/output access when expr is `<alias>.output...` or `<alias>.records...`.

    Returns None for unrecognized shapes.
    """
    slices: list[cst.SubscriptElement] = []
    current: cst.BaseExpression = expr

    while isinstance(current, cst.Subscript):
        # current.slice may be a Sequence[SubscriptElement] or a single SubscriptElement.
        slice_val = current.slice
        # If it's a sequence, insert its elements preserving order; otherwise insert the single element.
        if isinstance(slice_val, list | tuple):
            # Prepend all elements preserving order
            slices[0:0] = list(slice_val)
        else:
            # mypy cannot always narrow `slice_val` to a single SubscriptElement, so cast it here.
            slices.insert(0, cast(cst.SubscriptElement, slice_val))
        # `current.value` is the expression being subscripted (the next node up)
        current = current.value

    if (
        isinstance(current, cst.Attribute)
        and isinstance(current.value, cst.Name)
        and isinstance(current.attr, cst.Name)
        and current.attr.value in {"output", "records"}
    ):
        return AliasOutputAccess(alias_name=current.value.value, slices=tuple(slices))

    return None


def build_caplog_records_expr(access: AliasOutputAccess) -> cst.BaseExpression:
    """Construct `caplog.records` expression and apply subscripts from access.slices."""
    base: cst.BaseExpression = cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="records"))
    for slice_item in access.slices:
        # cst.Subscript expects a sequence of SubscriptElement for the `slice` parameter.
        base = cst.Subscript(value=base, slice=(slice_item,))
    return base


def build_get_message_call(access: AliasOutputAccess) -> cst.Call:
    """Construct `caplog.records[...].getMessage()` call for the provided access."""
    return cst.Call(
        func=cst.Attribute(value=build_caplog_records_expr(access), attr=cst.Name(value="getMessage")), args=[]
    )
