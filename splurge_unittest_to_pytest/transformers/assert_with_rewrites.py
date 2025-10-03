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


def _build_get_message_call(access: "_orig.AliasOutputAccess") -> cst.Call:
    return _orig._build_get_message_call(access)


__all__ = ["_extract_alias_output_slices", "_build_caplog_records_expr"]


def _create_robust_regex(pattern: str) -> str:
    """Delegate robust regex creation to the original module (conservative shim)."""
    try:
        return _orig._create_robust_regex(pattern)
    except Exception:
        return pattern


def transform_caplog_alias_string_fallback(code: str) -> str:
    """Delegate string-level caplog alias fallbacks to the original implementation."""
    try:
        return _orig.transform_caplog_alias_string_fallback(code)
    except Exception:
        return code


def transform_assert_dict_equal(node: cst.Call) -> cst.CSTNode:
    """Delegate assert-dict-equal transform to AST rewrites shim."""
    try:
        return _orig.transform_assert_dict_equal(node)
    except Exception:
        return node


__all__.extend(["_create_robust_regex", "transform_caplog_alias_string_fallback", "transform_assert_dict_equal"])


def _rewrite_membership_comparison(
    comp_node: cst.Comparison,
    alias_name: str,
) -> cst.Comparison | None:
    """Rewrite membership checks against ``<alias>.output`` to ``getMessage()`` calls.

    Defensive: use isinstance checks and avoid assumptions about node shapes.
    """
    new_targets: list[cst.ComparisonTarget] = []
    changed = False

    for target in getattr(comp_node, "comparisons", ()):
        # Only handle 'in' operators
        if isinstance(getattr(target, "operator", None), cst.In):
            comp = getattr(target, "comparator", None)
            if comp is None:
                new_targets.append(target)
                continue
            access = _extract_alias_output_slices(comp)
            if access is not None and access.alias_name == alias_name:
                new_targets.append(
                    cst.ComparisonTarget(operator=target.operator, comparator=_build_get_message_call(access))
                )
                changed = True
                continue

        new_targets.append(target)

    if changed:
        return comp_node.with_changes(comparisons=new_targets)

    return None


def _rewrite_equality_comparison(
    comp_node: cst.Comparison,
    alias_name: str,
) -> cst.Comparison | None:
    """Rewrite equality checks touching ``<alias>.output`` to pytest-friendly expressions.

    This is a conservative subset of the original implementation: it handles
    direct cases where the left expression is a Subscript or Attribute that
    targets ``<alias>.output`` and rewrites it to either a ``getMessage()``
    call (for Subscript) or a ``caplog.records`` expression (for Attribute).
    """
    changed = False
    new_left = getattr(comp_node, "left", None)
    left_access = None

    if isinstance(new_left, cst.Subscript | cst.Attribute):
        # mypy may not narrow here; _extract_alias_output_slices is defensive
        left_access = _extract_alias_output_slices(new_left)
    if left_access is not None and left_access.alias_name == alias_name:
        if isinstance(new_left, cst.Subscript):
            new_left = _build_get_message_call(left_access)
        else:
            new_left = _build_caplog_records_expr(left_access)
        changed = True

    if changed:
        return comp_node.with_changes(left=new_left)

    return None


def _rewrite_comparison(comp_node: cst.Comparison, alias_name: str) -> cst.Comparison | None:
    """Apply all comparison rewrite helpers and return the updated node when changes occur."""

    rewritten = comp_node
    changed = False

    for rewriter in (
        _rewrite_length_comparison,
        _rewrite_membership_comparison,
        _rewrite_equality_comparison,
    ):
        try:
            candidate = rewriter(rewritten, alias_name)
        except Exception:
            candidate = None
        if candidate is not None:
            rewritten = candidate
            changed = True

    return rewritten if changed else None


def _rewrite_unary_operation(unary: cst.UnaryOperation, alias_name: str) -> cst.UnaryOperation | None:
    """Rewrite unary operations that reference ``<alias>.output`` inside their expressions."""

    inner = getattr(unary, "expression", None)

    try:
        rewritten_inner = _rewrite_expression(inner, alias_name) if inner is not None else None
    except Exception:
        rewritten_inner = None

    if rewritten_inner is not None:
        # If the inner was a comparison, preserve parentheses metadata when present
        if isinstance(inner, cst.Comparison):
            parens = _orig.parenthesized_expression(inner)
            comparison_result = rewritten_inner
            if (
                isinstance(comparison_result, cst.Comparison)
                and len(inner.comparisons) == 1
                and isinstance(inner.comparisons[0].operator, cst.In)
            ):
                comparator_expr = comparison_result.comparisons[0].comparator
                return unary.with_changes(expression=parens.strip(comparator_expr))
            # Otherwise restore potentially stripped parens
            rewritten_inner = parens.strip(comparison_result)
        return unary.with_changes(expression=rewritten_inner)

    if not isinstance(inner, cst.Comparison):
        return None

    rewritten_comp = _rewrite_comparison(inner, alias_name)
    if rewritten_comp is None:
        return None

    parens = _orig.parenthesized_expression(inner)
    if len(rewritten_comp.comparisons) == 1 and isinstance(rewritten_comp.comparisons[0].operator, cst.In):
        comparator_expr = rewritten_comp.comparisons[0].comparator
        return unary.with_changes(expression=parens.strip(comparator_expr))

    stripped = parens.strip(rewritten_comp)
    return unary.with_changes(expression=stripped)


def _replace_exception_attr_in_expr(expr: cst.BaseExpression, alias_name: str) -> cst.BaseExpression | None:
    """Detect and replace ``<alias>.exception`` with ``<alias>.value`` inside expressions.

    Returns a replacement expression when a change is made, otherwise None.
    """
    # Direct attribute: <alias>.exception
    if isinstance(expr, cst.Attribute) and isinstance(expr.value, cst.Name):
        if expr.value.value == alias_name and isinstance(expr.attr, cst.Name) and expr.attr.value == "exception":
            return expr.with_changes(attr=cst.Name(value="value"))

    # Call wrapping attribute: e.g., str(<alias>.exception)
    if isinstance(expr, cst.Call) and getattr(expr, "args", None):
        try:
            inner = expr.args[0].value
            replaced = _replace_exception_attr_in_expr(inner, alias_name)
            if replaced is not None:
                new_args = [cst.Arg(value=replaced)] + list(expr.args[1:])
                return expr.with_changes(args=new_args)
        except Exception:
            pass

    return None


def _rewrite_expression(expr: cst.BaseExpression | None, alias_name: str) -> cst.BaseExpression | None:
    """Recursively rewrite expressions that reference ``<alias>.output``."""

    if expr is None:
        return None

    if isinstance(expr, cst.Comparison):
        # preserve parentheses when rewriting
        try:
            rewritten = _rewrite_comparison(expr, alias_name)
        except Exception:
            rewritten = None
        return rewritten

    if isinstance(expr, cst.BooleanOperation):
        new_left = _rewrite_expression(expr.left, alias_name)
        new_right = _rewrite_expression(expr.right, alias_name)
        if new_left is not None or new_right is not None:
            return expr.with_changes(
                left=new_left if new_left is not None else expr.left,
                right=new_right if new_right is not None else expr.right,
            )
        return None

    if isinstance(expr, cst.UnaryOperation):
        return _rewrite_unary_operation(expr, alias_name)

    return None


def _rewrite_length_comparison(
    comp_node: cst.Comparison,
    alias_name: str,
) -> cst.Comparison | None:
    """Rewrite ``len(<alias>.output...)`` comparisons to ``len(caplog.records...)``.

    Returns a modified Comparison when a rewrite was performed, otherwise None.
    """
    # Defensive guards: ensure shapes are what we expect before accessing attrs
    left = getattr(comp_node, "left", None)
    if not isinstance(left, cst.Call) or not isinstance(getattr(left, "func", None), cst.BaseExpression):
        return None
    # Ensure the call is a 'len(...)' invocation
    func = getattr(left, "func", None)
    if not isinstance(func, cst.Name) or func.value != "len" or not getattr(left, "args", None):
        return None

    try:
        arg0 = left.args[0].value
    except Exception:
        return None

    access = _extract_alias_output_slices(arg0)
    if access is not None and access.alias_name == alias_name:
        new_arg = _build_caplog_records_expr(access)
        new_left = left.with_changes(args=[cst.Arg(value=new_arg)])
        return comp_node.with_changes(left=new_left)

    return None


def _safe_extract_statements(body_container, max_depth: int = 7) -> list[cst.BaseStatement] | None:
    """Safely extract a list of statements from a body container.

    This is a small, well-typed copy of the helper from
    `assert_transformer` used during the staged migration so the
    orchestration code can call it without creating circular imports.
    It returns None when the body cannot be interpreted as a list of
    statements.
    """
    if body_container is None or not hasattr(body_container, "body"):
        return None

    current = body_container.body
    depth = 0
    while depth < max_depth:
        # Accept actual lists/tuples of statements. However some libcst
        # shapes produce a one-element list containing another container
        # (for example an IndentedBlock nested inside a list). In that
        # case unwrap the single element and continue drilling.
        if isinstance(current, list | tuple):
            # If it's a single-element list and that element itself
            # exposes a .body, step into it and continue unwrapping.
            if len(current) == 1 and hasattr(current[0], "body"):
                current = current[0].body
                depth += 1
                continue
            return list(current)
        # Otherwise, if it exposes a nested .body, drill into it
        if hasattr(current, "body"):
            current = current.body
            depth += 1
            continue
        # Unexpected structure: bail out
        return None

    return None


def _handle_simple_statement_line(
    stmt: cst.SimpleStatementLine, statements: list[cst.BaseStatement], i: int
) -> tuple[list[cst.BaseStatement], int, bool] | None:
    """Handle a SimpleStatementLine that might contain a bare assert call.

    Delegates to the project's existing bare-assert handler when available
    and reports transformation errors defensively.
    """
    if not (len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr)):
        return None

    try:
        # Delegate to the existing handler where implemented
        return _orig.handle_bare_assert_call(statements, i)
    except (AttributeError, TypeError, IndexError) as e:
        _orig.report_transformation_error(
            e,
            "assert_with_rewrites",
            "_handle_simple_statement_line",
            suggestions=["Check statement structure in transformation"],
        )
        return ([], 0, False)


def _handle_with_statement(stmt: cst.With, statements: list[cst.BaseStatement], i: int) -> cst.With | None:
    """Handle a With statement that might need transformation; wrap processing with error reporting."""
    try:
        return _orig._process_with_statement(stmt, statements, i)
    except (AttributeError, TypeError, IndexError) as e:
        _orig.report_transformation_error(
            e,
            "assert_with_rewrites",
            "_handle_with_statement",
            suggestions=["Check With statement structure in transformation"],
        )
        return None


def _handle_try_statement(stmt: cst.BaseStatement, max_depth: int = 7) -> cst.BaseStatement | None:
    """Handle a Try statement with recursive processing and error reporting."""
    try:
        return _orig._process_try_statement(stmt, max_depth)
    except (AttributeError, TypeError, IndexError) as e:
        _orig.report_transformation_error(
            e,
            "assert_with_rewrites",
            "_handle_try_statement",
            suggestions=["Check Try statement structure in transformation"],
        )
        return None


def get_self_attr_call(stmt: cst.BaseStatement) -> tuple[str, cst.Call] | None:
    """Return (attribute_name, Call) for bare self/cls calls like ``self.foo(...)``.

    This inspects ``stmt`` and returns the attribute name and call node when
    the statement is a single-expression call to an attribute on ``self`` or
    ``cls``. Otherwise returns ``None``.
    """
    if not isinstance(stmt, cst.SimpleStatementLine):
        return None
    if not (len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr)):
        return None
    expr = stmt.body[0].value
    if not isinstance(expr, cst.Call):
        return None
    func = expr.func
    if not isinstance(func, cst.Attribute):
        return None
    value = func.value
    if not isinstance(value, cst.Name) or value.value not in {"self", "cls"}:
        return None
    # attribute name may be a Name node
    if isinstance(func.attr, cst.Name):
        return func.attr.value, expr
    return None  # type: ignore[unreachable]


# Explicit mapping from unittest assert method name -> original module transform function name.
# This is clearer and easier to extend than an ad-hoc CamelCase->snake_case heuristic.
ASSERT_METHOD_TO_TRANSFORM: dict[str, str] = {
    "assertEqual": "transform_assert_equal",
    "assertNotEqual": "transform_assert_not_equal",
    "assertIn": "transform_assert_in",
    "assertNotIn": "transform_assert_not_in",
    "assertTrue": "transform_assert_true",
    "assertFalse": "transform_assert_false",
    "assertIs": "transform_assert_is",
    "assertIsNot": "transform_assert_is_not",
    "assertIsNone": "transform_assert_is_none",
    "assertIsNotNone": "transform_assert_is_not_none",
    "assertRaises": "transform_assert_raises",
    "assertRaisesRegex": "transform_assert_raises_regex",
    "assertRegex": "transform_assert_regex",
    "assertNotRegex": "transform_assert_not_regex",
    "assertCountEqual": "transform_assert_count_equal",
    "assertAlmostEqual": "transform_assert_almost_equal",
    "assertGreater": "transform_assert_greater",
    "assertGreaterEqual": "transform_assert_greater_equal",
    "assertLess": "transform_assert_less",
    "assertLessEqual": "transform_assert_less_equal",
    "assertSequenceEqual": "transform_assert_sequence_equal",
    "assertListEqual": "transform_assert_list_equal",
    "assertTupleEqual": "transform_assert_tuple_equal",
    "assertSetEqual": "transform_assert_set_equal",
    "assertDictEqual": "transform_assert_dict_equal",
    "assertDictContainsSubset": "transform_assert_dict_contains_subset",
    "assertAlmostEquals": "transform_assert_almost_equal",  # alias spelling
    "assertItemsEqual": "transform_assert_items_equal",  # Py2 name sometimes encountered
}


def _lookup_transform_fn_for_assert_method(method_name: str):
    """Return a callable transform function from the original module for the
    given unittest method name, or None when not available.

    This centralizes the mapping and makes it easy to add additional
    assert-methods later. The mapping stores function names to avoid
    importing many symbols; we resolve them via getattr on the original
    module to preserve the delegation pattern used elsewhere in this file.
    """
    fn_name = ASSERT_METHOD_TO_TRANSFORM.get(method_name)
    if not fn_name:
        return None
    return getattr(_orig, fn_name, None)


def get_caplog_level_args(call_expr: cst.Call) -> list[cst.Arg]:
    """Extract args suitable for ``caplog.at_level`` from an ``assertLogs`` call.

    The unittest ``assertLogs(logger, level=...)`` convention places the
    level as the second positional argument or as a ``level=`` keyword. If
    not present default to the string "INFO".
    """
    # positional second arg: args[1]
    if getattr(call_expr, "args", None) and len(call_expr.args) >= 2:
        return [cst.Arg(value=call_expr.args[1].value)]
    # look for a keyword arg named 'level'
    for arg in getattr(call_expr, "args", ()):
        if getattr(arg, "keyword", None) and isinstance(arg.keyword, cst.Name) and arg.keyword.value == "level":
            return [cst.Arg(value=arg.value)]
    # default to "INFO"
    return [cst.Arg(value=cst.SimpleString(value='"INFO"'))]


def build_caplog_call(call_expr: cst.Call) -> cst.Call:
    """Construct a :class:`libcst.Call` for ``caplog.at_level(...)`` using level args."""
    args = get_caplog_level_args(call_expr)
    return cst.Call(func=cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="at_level")), args=args)


# --- Backwards-compatible delegations for orchestration helpers ---
def build_with_item_from_assert_call(call_expr: cst.Call) -> cst.WithItem | None:
    """Map known unittest assert-* calls (self.assertLogs, self.assertRaises, etc.) to pytest context managers.

    Conservative: return None when the call shape isn't recognized.
    """
    # Ensure we have a function attribute on the call
    func = getattr(call_expr, "func", None)
    if not isinstance(func, cst.Attribute) or not isinstance(func.value, cst.Name):
        return None
    owner = func.value.value
    if owner not in {"self", "cls"}:
        return None
    name = func.attr.value if isinstance(func.attr, cst.Name) else None
    if not name:
        return None

    # assertLogs / assertNoLogs -> caplog.at_level
    if name in {"assertLogs", "assertNoLogs"}:
        return cst.WithItem(item=build_caplog_call(call_expr), asname=None)

    # assertWarns / assertRaises -> pytest.warns / pytest.raises
    if name in {"assertWarns", "assertWarnsRegex"}:
        # For assertWarnsRegex the second positional arg is the regex to
        # match; pytest.warns expects this as the keyword 'match'. Convert
        # the second positional argument into a keyword arg named 'match'
        # when present. Preserve other args/keywords.
        orig_args = list(getattr(call_expr, "args", ()))
        new_args: list[cst.Arg] = []
        if name == "assertWarnsRegex" and len(orig_args) >= 2:
            # first arg remains positional (the exception)
            new_args.append(orig_args[0])
            # second arg becomes keyword 'match'
            second = orig_args[1]
            new_args.append(cst.Arg(value=second.value, keyword=cst.Name(value="match")))
            # append remaining original args as-is (starting from index 2)
            for a in orig_args[2:]:
                new_args.append(a)
        else:
            new_args = orig_args

        return cst.WithItem(
            item=cst.Call(
                func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="warns")), args=new_args
            ),
            asname=None,
        )
    if name == "assertRaises":
        return cst.WithItem(
            item=cst.Call(
                func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="raises")),
                args=list(getattr(call_expr, "args", ())),
            ),
            asname=None,
        )

    return None


def create_with_wrapping_next_stmt(
    with_item: cst.WithItem, next_stmt: cst.BaseStatement | None
) -> tuple[cst.With, int]:
    """Create a With node for a single WithItem, optionally wrapping next_stmt inside the with-body.

    Returns (with_node, consumed_count).
    """
    if next_stmt is None:
        # Use an Expr(Name('pass')) inside a SimpleStatementLine so the
        # resulting AST string matches the tests' expectations (some test
        # assertions expect a Name('pass') inside the SimpleStatementLine).
        pass_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))])
        body = cst.IndentedBlock(body=[pass_stmt])
        return (cst.With(items=[with_item], body=body), 1)

    # If provided statement is already a SimpleStatementLine or IndentedBlock, reuse
    if isinstance(next_stmt, cst.SimpleStatementLine):
        body = cst.IndentedBlock(body=[next_stmt])
        return (cst.With(items=[with_item], body=body), 2)

    # Otherwise wrap the statement into a SimpleStatementLine
    try:
        body = cst.IndentedBlock(body=[next_stmt])
        return (cst.With(items=[with_item], body=body), 2)
    except Exception:
        # Conservative fallback
        body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
        return (cst.With(items=[with_item], body=body), 1)


def handle_bare_assert_call(statements: list[cst.BaseStatement], i: int) -> tuple[list[cst.BaseStatement], int, bool]:
    """Detect bare self/cls assert-calls like ``self.assertLogs(...)`` and convert to With nodes.

    Returns (nodes_to_append, consumed_count, handled).
    """
    if i < 0 or i >= len(statements):
        return ([], 0, False)
    stmt = statements[i]
    if not isinstance(stmt, cst.SimpleStatementLine):
        return ([], 0, False)
    if not (len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr)):
        return ([], 0, False)
    expr = stmt.body[0].value
    if not isinstance(expr, cst.Call) or not isinstance(expr.func, cst.Attribute):
        return ([], 0, False)

    # Check owner is self/cls
    owner = expr.func.value
    if not isinstance(owner, cst.Name) or owner.value not in {"self", "cls"}:
        return ([], 0, False)

    with_item = build_with_item_from_assert_call(expr)
    if with_item is None:
        return ([], 0, False)

    # Attempt to wrap the following statement if present
    next_stmt = statements[i + 1] if i + 1 < len(statements) else None
    with_node, consumed = create_with_wrapping_next_stmt(with_item, next_stmt)
    return ([with_node], consumed, True)


def transform_with_items(stmt: cst.With) -> tuple[cst.With, str | None, bool]:
    """Convert With.items that use self/cls assert helpers to pytest equivalents.

    Returns (new_with, alias_name, changed)
    """
    items = getattr(stmt, "items", ())
    new_items: list[cst.WithItem] = []
    alias_name: str | None = None
    changed = False

    for it in items:
        # Attempt to extract a Call from the WithItem
        call = getattr(it, "item", None)
        # In some libcst versions the attribute is 'context_expr'
        if call is None:
            call = getattr(it, "context_expr", None)
        if not isinstance(call, cst.Call):
            new_items.append(it)
            continue

        built = build_with_item_from_assert_call(call)
        if built is None:
            new_items.append(it)
            continue

        # Preserve asname if present on the original
        try:
            asname = it.asname
        except Exception:
            asname = None
        built = built.with_changes(asname=asname)
        new_items.append(built)
        changed = True

        # capture alias name if present on original
        if (
            alias_name is None
            and getattr(it, "asname", None)
            and isinstance(it.asname, cst.AsName)
            and isinstance(it.asname.name, cst.Name)
        ):
            alias_name = it.asname.name.value

    if not changed:
        return (stmt, alias_name, False)

    new_with = stmt.with_changes(items=new_items)
    return (new_with, alias_name, True)


def get_with_alias_name(items: list[cst.WithItem]) -> str | None:
    for it in items:
        try:
            if it.asname and isinstance(it.asname, cst.AsName) and isinstance(it.asname.name, cst.Name):
                return it.asname.name.value
        except Exception:
            continue
    return None


def rewrite_single_alias_assert(target_assert: cst.Assert, alias_name: str) -> cst.Assert | None:
    """Rewrite a single Assert node referencing <alias>.output using expression rewriters in this module."""
    test = getattr(target_assert, "test", None)
    if test is None:
        return None

    try:
        # Prefer the original module's expression rewriter when possible because
        # it contains the more complete comparator-handling logic (getMessage,
        # caplog.records, exception.attr replacement). Fall back to the local
        # rewriter if the original is not available or raises.
        try:
            rewritten = _orig._rewrite_expression(test, alias_name)
        except Exception:
            rewritten = _rewrite_expression(test, alias_name)
    except Exception:
        rewritten = None

    if rewritten is not None:
        return target_assert.with_changes(test=rewritten)
    return None


def rewrite_asserts_using_alias_in_with_body(new_with: cst.With, alias_name: str) -> cst.With:
    stmts = _safe_extract_statements(new_with.body)
    if stmts is None:
        return new_with

    changed = False
    new_stmts: list[cst.BaseStatement] = []
    for s in stmts:
        # Handle SimpleStatementLine that wraps a single Assert (common libcst shape)
        if isinstance(s, cst.SimpleStatementLine):
            body = getattr(s, "body", None)
            if isinstance(body, list | tuple) and len(body) == 1 and isinstance(body[0], cst.Assert):
                inner = body[0]
                try:
                    r = rewrite_single_alias_assert(inner, alias_name)
                except Exception:
                    r = None
                if r is not None:
                    # preserve the SimpleStatementLine wrapper and replace the inner Assert
                    new_stmts.append(s.with_changes(body=[r]))
                    changed = True
                    continue

        # Also defensively handle a bare Assert node (unwrap/rewrap to a statement)
        if isinstance(s, cst.Assert):
            try:
                r = rewrite_single_alias_assert(s, alias_name)
            except Exception:
                r = None
            if r is not None:
                # wrap rewritten Assert into a SimpleStatementLine so IndentedBlock.body
                # contains valid Statement nodes rather than raw small-statement nodes.
                new_stmts.append(cst.SimpleStatementLine(body=[r]))
                changed = True
                continue

        new_stmts.append(s)

    if not changed:
        return new_with

    # Preserve the original IndentedBlock's formatting metadata where
    # possible by using the existing body.with_changes(...) helper. This
    # avoids creating a fresh IndentedBlock that may lack newline/indent
    # tokens and produce invalid generated code (see tests that assert
    # transformed code parses cleanly).
    try:
        orig_body = getattr(new_with, "body", None)
        if orig_body is not None and hasattr(orig_body, "with_changes"):
            return new_with.with_changes(body=orig_body.with_changes(body=new_stmts))
    except Exception:
        pass

    # Fallback: construct a fresh IndentedBlock if we can't preserve the
    # original metadata. This is conservative but may lose some formatting.
    return new_with.with_changes(body=cst.IndentedBlock(body=new_stmts))


def rewrite_following_statements_for_alias(
    statements: list[cst.BaseStatement], start_index: int, alias_name: str, look_ahead: int = 12
) -> None:
    end = min(len(statements), start_index + look_ahead)
    for idx in range(start_index, end):
        try:
            s = statements[idx]
            # Handle SimpleStatementLine containing a self/cls assert* call
            # e.g. ``self.assertEqual(len(log.output), 1)``. Convert known
            # assertX calls into their AST-shaped Assert form using the
            # original module's transform_assert_* helpers, then attempt
            # to rewrite the resulting Assert for alias references.
            if isinstance(s, cst.SimpleStatementLine):
                body = getattr(s, "body", None)
                if isinstance(body, list | tuple) and len(body) == 1 and isinstance(body[0], cst.Expr):
                    expr = body[0].value
                    if isinstance(expr, cst.Call) and isinstance(expr.func, cst.Attribute):
                        func_attr = expr.func
                        owner = getattr(func_attr, "value", None)
                        # Only consider self/cls owned assert calls
                        if isinstance(owner, cst.Name) and owner.value in {"self", "cls"}:
                            attr = func_attr.attr
                            if isinstance(attr, cst.Name):
                                # Map known unittest assert method names to the
                                # original module's transform function using the
                                # explicit mapping helper. This is clearer and
                                # handles irregular names like 'assertRaisesRegex'.
                                mname = attr.value
                                transform_fn = _lookup_transform_fn_for_assert_method(mname)
                                if callable(transform_fn):
                                    try:
                                        transformed = transform_fn(expr)
                                    except Exception:
                                        transformed = None
                                    # If we get an Assert node back, attempt to
                                    # rewrite it for alias references and replace
                                    # the statement in-place when successful.
                                    if isinstance(transformed, cst.Assert):
                                        try:
                                            r = rewrite_single_alias_assert(transformed, alias_name)
                                        except Exception:
                                            r = None
                                        if r is not None:
                                            statements[idx] = cst.SimpleStatementLine(body=[r])
                                            continue
            # libCST often wraps top-level asserts in a SimpleStatementLine whose
            # body contains a single Assert node. Support both shapes so the
            # in-place rewrite updates the list correctly.
            if isinstance(s, cst.Assert):
                r = rewrite_single_alias_assert(s, alias_name)
                if r is not None:
                    # wrap Assert into a SimpleStatementLine so the list of
                    # statements (BaseStatement) remains well-typed
                    statements[idx] = cst.SimpleStatementLine(body=[r])
            elif isinstance(s, cst.SimpleStatementLine):
                # If the SimpleStatementLine contains exactly one small-statement
                # and it's an Assert, attempt to rewrite that inner Assert and
                # replace the SimpleStatementLine with an updated one when
                # rewriting occurred.
                body = getattr(s, "body", None)
                if isinstance(body, list | tuple) and len(body) == 1 and isinstance(body[0], cst.Assert):
                    inner = body[0]
                    r = rewrite_single_alias_assert(inner, alias_name)
                    if r is not None:
                        # replace the single-item body with the rewritten Assert
                        statements[idx] = s.with_changes(body=[r])
        except Exception:
            continue
    return None
