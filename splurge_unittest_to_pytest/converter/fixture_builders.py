"""Helpers to build fixtures from setup assignments and teardown cleanup."""

import libcst as cst

from .fixtures import create_fixture_with_cleanup, create_simple_fixture


def build_fixtures_from_setup_assignments(
    setup_assignments: dict[str, cst.BaseExpression],
    teardown_cleanup: dict[str, list[cst.BaseStatement]],
) -> tuple[dict[str, cst.FunctionDef], bool]:
    """Build fixture FunctionDef nodes from setup assignments.

    Returns a tuple of (fixtures_mapping, needs_pytest_import).
    """
    fixtures: dict[str, cst.FunctionDef] = {}
    for attr_name, value_expr in setup_assignments.items():
        # Check if this attribute appears in the teardown cleanup mapping
        cleanup_statements = teardown_cleanup.get(attr_name, [])
        if cleanup_statements:
            fixture_node = create_fixture_with_cleanup(attr_name, value_expr, cleanup_statements)
        else:
            fixture_node = create_simple_fixture(attr_name, value_expr)
        fixtures[attr_name] = fixture_node

    # When creating fixtures, pytest import will be required
    return fixtures, True
