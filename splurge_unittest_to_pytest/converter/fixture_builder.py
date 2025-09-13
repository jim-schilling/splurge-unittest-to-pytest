"""Helpers for building fixtures and sanitizing cleanup statements."""

from __future__ import annotations


import libcst as cst

from .name_replacer import replace_names_in_statements


def replace_attr_references_in_statements(
    statements: list[cst.BaseStatement], attr_name: str, value_name: str
) -> list[cst.BaseStatement]:
    """Delegate to the shared name replacer transformer to replace attribute references."""
    return replace_names_in_statements(statements, attr_name, value_name)
