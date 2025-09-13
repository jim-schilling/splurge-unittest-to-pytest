"""Import helper utilities for the converter.

Contains pure functions that inspect or modify a libcst.Module to add imports or remove them.
"""

from typing import Any
import libcst as cst
from libcst import matchers as m

from .import_helpers import make_pytest_import_stmt


def remove_unittest_importfrom(updated_node: cst.ImportFrom) -> cst.ImportFrom | cst.RemovalSentinel:
    """Remove ImportFrom nodes that import from unittest."""
    if m.matches(updated_node, m.ImportFrom(module=m.Name("unittest"))):
        return cst.RemovalSentinel.REMOVE
    return updated_node


def remove_unittest_import(updated_node: cst.Import) -> cst.Import | cst.RemovalSentinel:
    """Remove Import nodes that import unittest."""
    for alias in updated_node.names:
        if m.matches(alias, m.ImportAlias(name=m.Name("unittest"))):
            return cst.RemovalSentinel.REMOVE
    return updated_node


_make_pytest_import_stmt = make_pytest_import_stmt


def has_pytest_import(module_node: cst.Module) -> bool:
    for stmt in module_node.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.Import):
                for alias in first.names:
                    if isinstance(alias.name, cst.Name) and alias.name.value == "pytest":
                        return True
            if isinstance(first, cst.ImportFrom) and isinstance(first.module, cst.Name):
                if first.module.value == "pytest":
                    return True
    return False


def add_pytest_import(module_node: cst.Module) -> cst.Module:
    """Return a new module with a pytest import inserted at an appropriate position.

    This mirrors the previous inline logic: after module docstring, after existing imports,
    or at the top.
    """
    if has_pytest_import(module_node):
        return module_node

    pytest_import = _make_pytest_import_stmt()

    new_body: list[Any] = list(module_node.body)

    insert_pos = 0
    if new_body:
        first_stmt = new_body[0]
        if (
            isinstance(first_stmt, cst.SimpleStatementLine)
            and first_stmt.body
            and isinstance(first_stmt.body[0], cst.Expr)
            and isinstance(first_stmt.body[0].value, cst.SimpleString)
        ):
            insert_pos = 1

    for i, stmt in enumerate(new_body[insert_pos:], start=insert_pos):
        if (
            isinstance(stmt, cst.SimpleStatementLine)
            and stmt.body
            and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
        ):
            insert_pos = i + 1
        else:
            break

    new_body.insert(insert_pos, pytest_import)
    return module_node.with_changes(body=new_body)
