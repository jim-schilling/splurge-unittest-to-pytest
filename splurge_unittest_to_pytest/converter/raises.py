"""Helpers to build :mod:`pytest` raises context managers.

The helpers in this module construct :class:`libcst.Call` and
:class:`libcst.WithItem` nodes that represent ``pytest.raises(...)``
context managers. They are intentionally pure functions so they can be
tested independently from transformer state.
"""

from __future__ import annotations

from typing import Sequence

import libcst as cst

DOMAINS = ["converter", "exceptions"]


def make_pytest_raises_call(args: Sequence[cst.Arg]) -> cst.Call:
    """Return a pytest.raises call node for given args.

    If no exception argument is supplied, default to `Exception`.
    """
    func = cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises"))
    if len(args) >= 1:
        return cst.Call(func=func, args=[args[0]])
    return cst.Call(func=func, args=[cst.Arg(value=cst.Name("Exception"))])


def make_pytest_raises_regex_call(args: Sequence[cst.Arg]) -> cst.Call:
    """Return a pytest.raises call with a 'match=' parameter when available."""
    func = cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises"))
    if len(args) >= 2:
        return cst.Call(
            func=func,
            args=[
                args[0],
                cst.Arg(keyword=cst.Name("match"), value=args[1].value),
            ],
        )
    # Fallback to the simple form
    return make_pytest_raises_call(args[:1] if args else [])


def create_pytest_raises_withitem(method_name: str, args: Sequence[cst.Arg]) -> cst.WithItem:
    """Create a cst.WithItem representing a pytest.raises context for the
    given unittest assertRaises/assertRaisesRegex arguments.
    """
    func = cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises"))
    if method_name == "assertRaises":
        return cst.WithItem(item=cst.Call(func=func, args=args))
    # assertRaisesRegex -> include match= when present
    return cst.WithItem(
        item=cst.Call(
            func=func,
            args=[
                args[0],
                cst.Arg(keyword=cst.Name("match"), value=args[1].value),
            ]
            if len(args) >= 2
            else args,
        )
    )


# Associated domains for this module

__all__: list[str] = [
    "make_pytest_raises_call",
    "make_pytest_raises_regex_call",
    "create_pytest_raises_withitem",
]
