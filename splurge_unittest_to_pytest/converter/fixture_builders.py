"""Helpers to construct fixtures from setup assignments and teardown cleanup.

This module collects setup assignments and teardown cleanup and delegates
to lower-level helpers (for example, :func:`create_fixture_for_attribute`)
to build :class:`libcst.FunctionDef` nodes representing pytest fixtures.
It returns a mapping of fixture name → function node and a boolean
indicating whether a pytest import is required.

Publics:
    build_fixtures_from_setup_assignments: Build fixture FunctionDef nodes and indicate pytest import need.
"""

import libcst as cst

from .fixtures import (
    create_fixture_for_attribute,
)

DOMAINS = ["converter", "fixtures"]

# Associated domains for this module


def build_fixtures_from_setup_assignments(
    setup_assignments: dict[str, cst.BaseExpression],
    teardown_cleanup: dict[str, list[cst.BaseStatement]],
) -> tuple[dict[str, cst.FunctionDef], bool]:
    """Build fixture FunctionDef nodes from setup assignments.

    Returns a tuple of (fixtures_mapping, needs_pytest_import).
    """
    fixtures: dict[str, cst.FunctionDef] = {}
    for attr_name, value_expr in setup_assignments.items():
        # Delegate creation to create_fixture_for_attribute which centralizes
        # guarded/simple/autocreated-file behavior. This ensures self-referential
        # placeholders emit a runtime guard and autocreation logic is localized.
        fixture_node = create_fixture_for_attribute(attr_name, value_expr, teardown_cleanup)
        fixtures[attr_name] = fixture_node

    # When creating fixtures, pytest import will be required
    return fixtures, True
