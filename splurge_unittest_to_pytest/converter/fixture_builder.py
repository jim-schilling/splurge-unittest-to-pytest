"""Fixture builder helpers used when converting setup/teardown code.

Small helpers that assist in creating fixture function definitions and
sanitizing cleanup statements when the converter transforms instance
attributes into top-level fixtures. These utilities delegate heavier
transform work to shared name-replacer helpers.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

import libcst as cst

from .name_replacer import replace_names_in_statements

DOMAINS = ["converter", "fixtures"]

# Associated domains for this module


def replace_attr_references_in_statements(
    statements: list[cst.BaseStatement], attr_name: str, value_name: str
) -> list[cst.BaseStatement]:
    """Delegate to the shared name replacer transformer to replace attribute references."""
    return replace_names_in_statements(statements, attr_name, value_name)
