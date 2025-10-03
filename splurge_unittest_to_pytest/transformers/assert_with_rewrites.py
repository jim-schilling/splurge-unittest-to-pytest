"""Helpers that rewrite 'with' / context-manager assertion patterns.

This file is initially a shim delegating to ``assert_transformer`` to
reduce reviewer friction. Later we will move focused implementations
from ``assert_transformer.py`` into this file.
"""

import libcst as cst

from . import assert_transformer as _orig


def _extract_alias_output_slices(expr: cst.BaseExpression) -> "_orig.AliasOutputAccess | None":
    return _orig._extract_alias_output_slices(expr)


def _build_caplog_records_expr(access: "_orig.AliasOutputAccess") -> cst.BaseExpression:
    return _orig._build_caplog_records_expr(access)


__all__ = ["_extract_alias_output_slices", "_build_caplog_records_expr"]
