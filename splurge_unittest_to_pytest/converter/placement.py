"""Helpers for placing fixtures and nodes into module bodies.

This module contains utilities to insert fixture :class:`libcst.FunctionDef`
nodes into module bodies, typically after the last import statement.

Publics:
    insert_fixtures_into_module
"""

from typing import Any

import libcst as cst

DOMAINS = ["converter"]

# Associated domains for this module


def insert_fixtures_into_module(module_node: cst.Module, fixtures: dict[str, cst.FunctionDef]) -> cst.Module:
    """Insert fixture FunctionDef nodes into the module body after imports.

    Fixtures are inserted after the last import statement (Import or ImportFrom).
    """
    if not fixtures:
        return module_node

    new_body: list[Any] = list(module_node.body)

    insert_pos = 0
    for i, stmt in enumerate(new_body):
        # recognize top-level import statements
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, (cst.ImportFrom, cst.Import)):
                insert_pos = i + 1
            else:
                # stop at first non-import line
                break

    # Insert fixtures at the determined position, preserving order
    for name, fixture_node in fixtures.items():
        if insert_pos > 0:
            new_body.insert(insert_pos, cst.EmptyLine())
            insert_pos += 1

        new_body.insert(insert_pos, fixture_node)
        insert_pos += 1

    return module_node.with_changes(body=new_body)
