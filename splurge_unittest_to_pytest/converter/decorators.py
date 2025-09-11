"""Small helpers to construct decorator nodes used by fixtures."""

from __future__ import annotations

import libcst as cst


def build_pytest_fixture_decorator() -> cst.Decorator:
    """Return a `@pytest.fixture` Decorator node."""
    return cst.Decorator(
        decorator=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
    )
