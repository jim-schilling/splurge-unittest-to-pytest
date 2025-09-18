"""Construct a :class:`libcst.FunctionDef` node for pytest fixtures.

Small constructor helper that builds a :class:`libcst.FunctionDef` for a
fixture given a name, body block, and decorator. Kept minimal so tests
can directly assert expected node shapes.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

import libcst as cst

DOMAINS = ["converter", "fixtures"]

# Associated domains for this module


def create_fixture_function(
    attr_name: str,
    body: cst.IndentedBlock,
    decorator: cst.Decorator,
) -> cst.FunctionDef:
    """Return a FunctionDef for a fixture with the provided body and decorator."""
    return cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(),
        body=body,
        decorators=[decorator],
        returns=None,
        asynchronous=None,
    )
