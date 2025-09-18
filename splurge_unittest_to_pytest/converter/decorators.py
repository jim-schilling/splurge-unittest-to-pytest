"""Helpers to construct :mod:`libcst` decorator nodes for fixtures.

Provides :func:`build_pytest_fixture_decorator` which builds a
``@pytest.fixture`` decorator node, optionally accepting keyword
arguments (for example ``autouse=True``) in a deterministic order.

Publics:
    build_pytest_fixture_decorator: Build a canonical @pytest.fixture decorator node.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

import libcst as cst
from typing import Any, Mapping

DOMAINS = ["converter"]

# Associated domains for this module


def build_pytest_fixture_decorator(kwargs: Mapping[str, Any] | None = None, **explicit_kwargs: Any) -> cst.Decorator:
    """Return a `@pytest.fixture` Decorator node.

    When `kwargs` is None or empty, produce the canonical attribute form
    `@pytest.fixture`. When kwargs are present, produce a Call node such as
    `@pytest.fixture(autouse=True)`.
    """
    # Merge mapping and explicit kwargs; explicit keyword arguments take precedence.
    merged_kwargs: dict[str, Any] = {}
    if kwargs:
        merged_kwargs.update(kwargs)
    if explicit_kwargs:
        merged_kwargs.update(explicit_kwargs)

    if not merged_kwargs:
        return cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))

    # Build cst.Arg list from kwargs mapping. Accept simple Python primitives
    # (True/False/str/int) or libcst expression nodes. Keywords are emitted
    # in deterministic sorted order for stable output.
    args: list[cst.Arg] = []
    for key in sorted(merged_kwargs.keys()):
        val = merged_kwargs[key]
        if isinstance(val, cst.BaseExpression):
            value_node = val
        else:
            # Map common Python primitives to libcst literal nodes
            if val is True:
                value_node = cst.Name("True")
            elif val is False:
                value_node = cst.Name("False")
            elif val is None:
                value_node = cst.Name("None")
            elif isinstance(val, str):
                value_node = cst.SimpleString(repr(val))
            elif isinstance(val, int):
                value_node = cst.Integer(str(val))
            else:
                # Fallback: represent using Name() of the str() form
                value_node = cst.Name(str(val))

        args.append(cst.Arg(keyword=cst.Name(key), value=value_node))

    return cst.Decorator(
        decorator=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")), args=args)
    )
