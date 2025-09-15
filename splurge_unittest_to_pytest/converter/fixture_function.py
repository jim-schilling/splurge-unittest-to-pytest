"""Helper to construct a fixture FunctionDef node."""

from __future__ import annotations

import libcst as cst

DOMAINS = ["converter", "fixtures"]

# Associated domains for this module


def create_fixture_function(attr_name: str, body: cst.IndentedBlock, decorator: cst.Decorator) -> cst.FunctionDef:
    """Return a FunctionDef for a fixture with the provided body and decorator."""
    return cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(),
        body=body,
        decorators=[decorator],
        returns=None,
        asynchronous=None,
    )
