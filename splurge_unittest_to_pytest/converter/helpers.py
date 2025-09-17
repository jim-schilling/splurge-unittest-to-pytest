"""Canonical helper implementations for the converter package.

This module centralizes small, well-tested helpers used by the converter
stages. Helpers include name normalization, pattern parsing, AST
transform utilities, and change-detection routines.
"""

from __future__ import annotations

import ast
import re

import libcst as cst

DOMAINS = ["converter", "helpers"]

# Associated domains for this module


class SelfReferenceRemover(cst.CSTTransformer):
    """Remove ``self``/``cls`` references from attribute accesses.

    Useful when creating top-level functions from instance methods; the
    transformer replaces ``self.attr`` with ``attr`` by stripping the
    attribute's value when it references the instance name.
    """

    def __init__(self, param_names: set[str] | None = None) -> None:
        self.param_names = param_names or {"self", "cls"}

    def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.Attribute | cst.Name:
        if isinstance(updated_node.value, cst.Name) and updated_node.value.value in self.param_names:
            return updated_node.attr
        return updated_node


def normalize_method_name(name: str) -> str:
    """Normalize a method name for pattern matching.

    Converts CamelCase or mixedCase identifiers into snake_case which makes
    pattern matching and comparisons more predictable.
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def parse_method_patterns(pattern_args: tuple[str, ...] | list[str] | None) -> list[str]:
    """Parse method patterns supporting comma-separated values and multiple flags.

    Args:
        pattern_args: A tuple or list of pattern arguments as provided by the
            CLI or None.

    Returns:
        A list of unique pattern strings in their original order.
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
    """Return True if ``converted_code`` has meaningful differences from ``original_code``.

    The function uses three strategies in order:

    1. Normalize both modules with the project's formatting normalizer and
       compare the resulting source text.
    2. Compare Python AST dumps to ignore formatting-only differences.
    3. Fallback to direct text comparison.

    Returns:
        ``True`` if a meaningful difference is detected, otherwise ``False``.
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
