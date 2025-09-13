"""Canonical small helper implementations for the converter package.

This module centralizes small, well-tested helpers used internally by the
converter. It is the canonical location for normalization, parsing, and
change-detection helpers. These implementations were moved here during the
simplification refactor. Note: `converter.core` (a prior thin shim) was
removed to reduce indirection; consumers should import from this module if
they must access internal helpers.
"""

from __future__ import annotations

import ast
import re
from typing import List

import libcst as cst


class SelfReferenceRemover(cst.CSTTransformer):
    """Remove self/cls references from attribute accesses."""

    def __init__(self, param_names: set[str] | None = None) -> None:
        self.param_names = param_names or {"self", "cls"}

    def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.Attribute | cst.Name:
        if isinstance(updated_node.value, cst.Name) and updated_node.value.value in self.param_names:
            return updated_node.attr
        return updated_node


def normalize_method_name(name: str) -> str:
    """Normalize method name for pattern matching (convert camelCase to snake_case)."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def parse_method_patterns(pattern_args: tuple[str, ...] | list[str] | None) -> List[str]:
    """Parse method patterns supporting comma-separated values and multiple flags.

    Returns a list of unique patterns preserving order.
    """
    if not pattern_args:
        return []

    patterns: list[str] = []
    for arg in pattern_args:
        trimmed_arg = arg.strip()
        if not trimmed_arg:
            continue
        for part in trimmed_arg.split(","):
            trimmed = part.strip()
            if trimmed:
                patterns.append(trimmed)

    # remove duplicates while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for p in patterns:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def has_meaningful_changes(original_code: str, converted_code: str) -> bool:
    """Return True if converted_code has meaningful differences from original_code.

    This function tries three strategies in order:
    1. Normalize both modules using the project's formatting normalizer and compare.
    2. Compare the ASTs (ignoring formatting-only differences).
    3. Fallback to direct text comparison.
    """
    # Try formatting-normalized comparison first. If normalized modules are
    # identical, then there is no meaningful change. If they differ, do not
    # immediately declare a change -- fall back to AST comparison below so
    # we ignore formatting-only differences when possible.
    try:
        from ..stages import formatting

        orig_mod = cst.parse_module(original_code)
        conv_mod = cst.parse_module(converted_code)
        norm_orig = formatting.normalize_module(orig_mod).code
        norm_conv = formatting.normalize_module(conv_mod).code
        if norm_orig == norm_conv:
            return False
        # Otherwise, fall through to AST comparison before deciding
    except Exception:
        # If normalization fails, fall through to AST comparison
        pass

    try:
        ast_orig = ast.parse(original_code)
        ast_conv = ast.parse(converted_code)
        if ast.dump(ast_orig, include_attributes=False) != ast.dump(ast_conv, include_attributes=False):
            return True
        return False
    except Exception:
        pass

    return original_code != converted_code
