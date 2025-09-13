"""Helpers to build fixtures from setup assignments and teardown cleanup."""

import libcst as cst

from .fixtures import create_fixture_with_cleanup, create_simple_fixture_with_guard as create_simple_fixture
from .fixtures import create_autocreated_file_fixture


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
            # If value_expr is a trivial self-reference and there is a sibling
            # '<attr>_content' fixture available, auto-create a tmp_path-based
            # file fixture that writes the content. This handles common patterns
            # where setUp used a helper to create files from content.
            content_name = None
            if isinstance(attr_name, str) and attr_name.endswith('_file'):
                # look for sibling like 'sql_content' if attr_name is 'sql_file'
                prefix = attr_name[: -len('_file')]
                candidate = f"{prefix}_content"
                if candidate in setup_assignments:
                    content_name = candidate

            if content_name is not None:
                fixture_node = create_autocreated_file_fixture(attr_name, content_name)
            else:
                fixture_node = create_simple_fixture(attr_name, value_expr)
        fixtures[attr_name] = fixture_node

    # When creating fixtures, pytest import will be required
    return fixtures, True
