"""Small helpers to construct decorator nodes used by fixtures."""

from __future__ import annotations

import libcst as cst


def build_pytest_fixture_decorator() -> cst.Decorator:
    """Return a `@pytest.fixture` Decorator node."""
    # Use Attribute (no call) for the canonical `@pytest.fixture` form.
    return cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
