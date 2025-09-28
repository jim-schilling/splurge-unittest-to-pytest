"""Assertion transformation helpers.

This module contains helper functions used to convert unittest-style
assertions (for example, ``self.assertEqual(...)``) into equivalent
pytest-style assertions or expressions using libcst nodes. The
functions operate on libcst AST nodes and are intentionally
conservative: when an input shape is not recognized the helper will
return ``None`` (or the original node) so callers can safely fall back
to leaving the source unchanged.

These helpers handle common parser shapes produced by ``libcst`` such
as :class:`libcst.Comparison`, :class:`libcst.ParenthesizedExpression`,
:class:`libcst.BooleanOperation`, and :class:`libcst.UnaryOperation`.
They try to rewrite inner comparisons, walk into parenthesized or
unary wrappers, and recursively visit boolean operations. Consumers
should prefer the conservative behavior: return ``None`` when a
transformation cannot be performed precisely.

Only docstrings and comments were clarified in this module; no runtime
behavior is changed by the updates in this patch.
"""

from typing import cast

import libcst as cst


def transform_assert_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertEqual(a, b)`` to a bare ``assert a == b``.

    This function expects ``node`` to be a :class:`libcst.Call` that
    represents a ``self.assertEqual`` (or equivalent) invocation.

    Args:
        node: A :class:`libcst.Call` node for the original assertion call.

    Returns:
        A :class:`libcst.Assert` node performing ``a == b`` when the
        call has at least two positional arguments. If the call has
        fewer than two arguments the original node is returned
        unchanged.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_almost_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``assertNotAlmostEqual`` to a negated numeric comparison.

    The unittest form ``self.assertNotAlmostEqual(a, b, places=N)`` is
    approximated with ``assert not round(a - b, N) == 0``. If the
    ``places`` keyword is omitted this function uses ``7`` as the
    default number of decimal places to mirror unittest's default.

    Args:
        node: A :class:`libcst.Call` node for the original assertion call.

    Returns:
        A :class:`libcst.Assert` node containing a negated
        :class:`libcst.Comparison` using ``round`` when the call has at
        least two arguments. If the call is missing required arguments
        the original node is returned unchanged.
    """
    if len(node.args) >= 2:
        left = node.args[0].value
        right = node.args[1].value
        places = None
        for arg in node.args:
            if arg.keyword and isinstance(arg.keyword, cst.Name) and arg.keyword.value == "places":
                places = arg.value
                break
        if places is None:
            places = cst.Integer(value="7")
        diff = cst.BinaryOperation(left=left, operator=cst.Subtract(), right=right)
        round_call = cst.Call(func=cst.Name(value="round"), args=[cst.Arg(value=diff), cst.Arg(value=places)])
        comp = cst.Comparison(
            left=round_call,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer(value="0"))],
        )
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=comp))
    return node


def transform_assert_true(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertTrue(expr)`` to ``assert expr``.

    Args:
        node: A :class:`libcst.Call` node representing the original
            ``assertTrue`` invocation.

    Returns:
        A :class:`libcst.Assert` node with ``test`` set to the first
        positional argument when present; otherwise returns the input
        node unchanged.
    """
    if len(node.args) >= 1:
        return cst.Assert(test=node.args[0].value)
    return node


def transform_assert_false(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertFalse(expr)`` to ``assert not expr``.

    Args:
        node: A :class:`libcst.Call` node representing the original
            ``assertFalse`` invocation.

    Returns:
        A :class:`libcst.Assert` node containing a
        :class:`libcst.UnaryOperation` with operator ``Not`` and the
        supplied expression when at least one positional argument is
        present. Otherwise returns the input node unchanged.
    """
    if len(node.args) >= 1:
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=node.args[0].value))
    return node


def transform_assert_is(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertIs(a, b)`` to ``assert a is b``.

    Args:
        node: A :class:`libcst.Call` node representing the original
            ``assertIs`` invocation.

    Returns:
        A :class:`libcst.Assert` node performing an identity comparison
        when two positional arguments are provided; otherwise returns
        the original node.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertNotEqual(a, b)`` to ``assert a != b``.

    Returns a :class:`libcst.Assert` with an inequality comparison when
    two positional arguments exist; otherwise returns the input node.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.NotEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_not(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertIsNot(a, b)`` to ``assert a is not b``.

    Returns a :class:`libcst.Assert` with an identity-negative
    comparison when two positional arguments exist; otherwise returns
    the input node.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_none(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertIsNone(x)`` to ``assert x is None``.

    Returns a :class:`libcst.Assert` performing the comparison when a
    single positional argument is provided; otherwise returns the
    original node.
    """
    if len(node.args) >= 1:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=cst.Name(value="None"))],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_not_none(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertIsNotNone(x)`` to ``assert x is not None``.

    Returns a :class:`libcst.Assert` performing the comparison when a
    single positional argument is provided; otherwise returns the
    original node.
    """
    if len(node.args) >= 1:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name(value="None"))],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_in(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertNotIn(a, b)`` to ``assert a not in b``.

    Returns a :class:`libcst.Assert` performing the membership negation
    when two positional arguments are present; otherwise returns the
    original node.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.NotIn(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_isinstance(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertIsInstance(obj, cls)`` to ``assert isinstance(obj, cls)``.

    Returns a :class:`libcst.Assert` whose test is a call to
    :func:`isinstance` when two positional arguments are present; if
    not, the original node is returned.
    """
    if len(node.args) >= 2:
        isinstance_call = cst.Call(
            func=cst.Name(value="isinstance"),
            args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
        )
        return cst.Assert(test=isinstance_call)
    return node


def transform_assert_not_isinstance(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertNotIsInstance(obj, cls)`` to ``assert not isinstance(obj, cls)``.

    Returns an :class:`libcst.Assert` wrapping an ``isinstance`` call in
    a unary ``not`` when two positional arguments are present; otherwise
    returns the input node unchanged.
    """
    if len(node.args) >= 2:
        isinstance_call = cst.Call(
            func=cst.Name(value="isinstance"),
            args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
        )
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=isinstance_call))
    return node


def transform_assert_count_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertCountEqual(a, b)`` to ``assert sorted(a) == sorted(b)``.

    Uses ``sorted`` on both operands to achieve an order-insensitive
    equality check. Returns a :class:`libcst.Assert` when two
    positional arguments are provided; otherwise returns the original
    node.
    """
    if len(node.args) >= 2:
        left = cst.Call(func=cst.Name(value="sorted"), args=[cst.Arg(value=node.args[0].value)])
        right = cst.Call(func=cst.Name(value="sorted"), args=[cst.Arg(value=node.args[1].value)])
        comp = cst.Comparison(left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=right)])
        return cst.Assert(test=comp)
    return node


def transform_assert_multiline_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertMultiLineEqual(a, b)`` to ``assert a == b``.

    Returns a :class:`libcst.Assert` performing equality when two
    positional arguments are provided; otherwise returns the original
    node.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_regex(
    node: cst.Call, re_alias: str | None = None, re_search_name: str | None = None
) -> cst.CSTNode:
    """Rewrite ``self.assertRegex(text, pattern)`` to ``assert re.search(pattern, text)``.

    This function constructs a :func:`re.search` call using either an
    explicitly-provided ``re_search_name`` (for ``from re import search``)
    or an ``re_alias`` (defaulting to ``re``). The generated call is
    used as the test expression of a :class:`libcst.Assert`.

    Args:
        node: The original :class:`libcst.Call` node.
        re_alias: Optional module alias to use instead of ``re``.
        re_search_name: Optional function name to use when ``search`` was
            imported directly from the ``re`` module.

    Returns:
        A :class:`libcst.Assert` node representing the ``re.search``
        invocation when the call has at least two positional arguments;
        otherwise returns the original node.
    """
    if len(node.args) >= 2:
        # If caller imported `search` directly (from re import search), use that name
        if re_search_name:
            func: cst.BaseExpression = cst.Name(value=re_search_name)
        else:
            re_name = re_alias or "re"
            func = cst.Attribute(value=cst.Name(value=re_name), attr=cst.Name(value="search"))

        call = cst.Call(
            func=func,
            args=[cst.Arg(value=node.args[1].value), cst.Arg(value=node.args[0].value)],
        )
        return cst.Assert(test=call)
    return node


def transform_assert_not_regex(
    node: cst.Call, re_alias: str | None = None, re_search_name: str | None = None
) -> cst.CSTNode:
    """Rewrite ``self.assertNotRegex(text, pattern)`` to ``assert not re.search(pattern, text)``.

    See ``transform_assert_regex`` for how the ``re`` name is chosen.
    Returns a negated :class:`libcst.Assert` when applicable; otherwise
    returns the original node.
    """
    if len(node.args) >= 2:
        if re_search_name:
            func: cst.BaseExpression = cst.Name(value=re_search_name)
        else:
            re_name = re_alias or "re"
            func = cst.Attribute(value=cst.Name(value=re_name), attr=cst.Name(value="search"))

        call = cst.Call(func=func, args=[cst.Arg(value=node.args[1].value), cst.Arg(value=node.args[0].value)])
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=call))
    return node


def transform_assert_in(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertIn(a, b)`` to ``assert a in b``.

    Returns a :class:`libcst.Assert` performing the membership check
    when two positional arguments are present; otherwise returns the
    original node.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_raises(node: cst.Call) -> cst.CSTNode:
    """Approximate ``self.assertRaises(exc, callable, *args)`` with ``pytest.raises``.

    This function produces a :class:`libcst.Call` that represents a
    ``pytest.raises(exc, lambda: <callable>)`` invocation. It is an
    approximation intended to make many common patterns easier to
    migrate; callers may prefer to convert to an actual ``with
    pytest.raises(...): <body>`` block instead for multi-statement
    bodies.
    """
    if len(node.args) >= 2:
        exception_type = node.args[0].value
        code_to_test = node.args[1].value
        new_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="raises"))
        new_args = [
            cst.Arg(value=exception_type),
            cst.Arg(value=cst.Call(func=cst.Name(value="lambda"), args=[cst.Arg(value=code_to_test)])),
        ]
        return cst.Call(func=new_attr, args=new_args)
    return node


def transform_assert_raises_regex(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertRaisesRegex(exc, callable, regex)`` to ``pytest.raises(exc, match=regex)``.

    Only supports the simple positional form ``(exc, callable, regex)``
    and produces a :class:`libcst.Call` node. Complex usages are left
    unchanged.
    """
    # Only transform when at least 3 args are provided: (exc, callable, regex)
    if len(node.args) >= 3:
        exc = node.args[0].value
        match_arg = node.args[2].value
        args: list[cst.Arg] = [cst.Arg(value=exc)]
        args.append(cst.Arg(keyword=cst.Name(value="match"), value=match_arg))
        return cst.Call(func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="raises")), args=args)
    return node


def get_self_attr_call(stmt: cst.BaseStatement) -> tuple[str, cst.Call] | None:
    """Return a (attribute_name, Call) tuple for bare ``self/cls`` calls.

    Inspects ``stmt`` and if it's a single-expression statement where
    the expression is a call to an attribute on ``self`` or ``cls``
    (for example ``self.foo(...)`` or ``cls.bar(...)``) returns a
    tuple of the attribute name (``'foo'``) and the :class:`libcst.Call`
    node. Returns ``None`` for any other shapes.
    """
    if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
        expr = stmt.body[0].value
        if isinstance(expr, cst.Call) and isinstance(expr.func, cst.Attribute):
            func = expr.func
            if isinstance(func.value, cst.Name) and func.value.value in {"self", "cls"}:
                return func.attr.value, expr
    return None


def get_caplog_level_args(call_expr: cst.Call) -> list[cst.Arg]:
    """Extract arguments suitable for ``caplog.at_level`` from an assertLogs call.

    The unittest ``assertLogs(logger, level=...)`` convention places the
    level as the second positional argument or as a ``level=`` keyword.
    This helper returns a list of :class:`libcst.Arg` to be passed to
    ``caplog.at_level(...)`. When no level is supplied it defaults to
    ``"INFO"``.
    """
    level_arg = call_expr.args[1] if len(call_expr.args) >= 2 else None
    if level_arg is None:
        for a in call_expr.args:
            if a.keyword and isinstance(a.keyword, cst.Name) and a.keyword.value == "level":
                level_arg = a
                break

    caplog_level_args: list[cst.Arg] = []
    if level_arg:
        level_value = level_arg.value if isinstance(level_arg, cst.Arg) else level_arg.value
        caplog_level_args.append(cst.Arg(value=level_value))
    else:
        caplog_level_args.append(cst.Arg(value=cst.SimpleString(value='"INFO"')))

    return caplog_level_args


def build_caplog_call(call_expr: cst.Call) -> cst.Call:
    """Construct a :class:`libcst.Call` node for ``caplog.at_level(...)``.

    Args:
        call_expr: The original :class:`libcst.Call` for
            ``self.assertLogs``/``self.assertNoLogs``.

    Returns:
        A :class:`libcst.Call` whose ``func`` is the
        ``caplog.at_level`` attribute and whose args are the level
        arguments (defaulting to ``"INFO"`` when not specified).
    """
    args = get_caplog_level_args(call_expr)
    return cst.Call(func=cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="at_level")), args=args)


def build_with_item_from_assert_call(call_expr: cst.Call) -> cst.WithItem | None:
    """Build a pytest-compatible :class:`libcst.WithItem` from a ``self``/``cls`` call.

    This recognizes common unittest context-manager-style assertions such
    as ``assertWarns``, ``assertRaises``, and ``assertLogs`` and returns
    a :class:`libcst.WithItem` representing the equivalent
    ``pytest.warns``, ``pytest.raises`` or ``caplog.at_level`` call.

    Args:
        call_expr: A :class:`libcst.Call` node whose ``func`` is an
            attribute lookup on ``self`` or ``cls``.

    Returns:
        A :class:`libcst.WithItem` when the input maps to a known
        pytest context manager; otherwise ``None``.
    """
    if not isinstance(call_expr.func, cst.Attribute):
        return None
    func = call_expr.func
    if not (isinstance(func.value, cst.Name) and func.value.value in {"self", "cls"}):
        return None

    attr_name = func.attr.value

    if attr_name in {"assertWarns", "assertWarnsRegex"}:
        exc_arg = call_expr.args[0] if call_expr.args else None
        match_arg = call_expr.args[1] if len(call_expr.args) >= 2 else None
        warn_items_args: list[cst.Arg] = []
        if exc_arg:
            warn_items_args.append(cst.Arg(value=exc_arg.value))
        if match_arg:
            warn_items_args.append(cst.Arg(keyword=cst.Name(value="match"), value=match_arg.value))
        warn_call = cst.Call(
            func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="warns")),
            args=warn_items_args,
        )
        return cst.WithItem(item=warn_call)

    if attr_name in {"assertRaises", "assertRaisesRegex"}:
        exc_arg = call_expr.args[0] if call_expr.args else None
        raises_items_args: list[cst.Arg] = []
        if exc_arg:
            raises_items_args.append(cst.Arg(value=exc_arg.value))
        raises_call = cst.Call(
            func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="raises")),
            args=raises_items_args,
        )
        return cst.WithItem(item=raises_call)

    if attr_name in {"assertLogs", "assertNoLogs"}:
        caplog_level_args = get_caplog_level_args(call_expr)

        cap_call = cst.Call(
            func=cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="at_level")),
            args=caplog_level_args,
        )
        return cst.WithItem(item=cap_call)

    return None


def create_with_wrapping_next_stmt(
    with_item: cst.WithItem, next_stmt: cst.BaseStatement | None
) -> tuple[cst.With, int]:
    """Create a :class:`libcst.With` node wrapping an optional following statement.

    The helper returns ``(with_node, consumed_count)`` where ``consumed_count``
    is ``2`` when a following statement was wrapped into the new with-body
    (the transformer should advance by 2), or ``1`` when no following
    statement exists and a ``pass`` node is used as the with-body.
    """
    if next_stmt is not None:
        if isinstance(next_stmt, cst.With):
            inner_body = getattr(next_stmt.body, "body", [])
            body_block = cst.IndentedBlock(body=cast(list[cst.BaseStatement], inner_body))
        else:
            body_block = cst.IndentedBlock(body=cast(list[cst.BaseStatement], [next_stmt]))
        with_node = cst.With(body=body_block, items=[with_item])
        return with_node, 2
    else:
        pass_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))])
        body_block = cst.IndentedBlock(body=cast(list[cst.BaseStatement], [pass_stmt]))
        with_node = cst.With(body=body_block, items=[with_item])
        return with_node, 1


def handle_bare_assert_call(statements: list[cst.BaseStatement], i: int) -> tuple[list[cst.BaseStatement], int, bool]:
    """Handle a bare ``self``/``cls`` assert-call statement.

    Examines ``statements[i]`` and, when it is a bare expression that
    calls a known unittest context manager (for example
    ``self.assertLogs(...)`` or ``self.assertRaises(...)``), returns a
    list of new statements to append, the number of input statements
    consumed, and ``True`` to indicate the call was handled. When the
    statement is not a recognized bare assert-call the function returns
    ``([], 0, False)``.

    Args:
        statements: The list of statements in the current block.
        i: Index of the statement to inspect.

    Returns:
        A tuple of ``(nodes_to_append, consumed_count, handled)``.
    """
    try:
        if i >= len(statements):
            return [], 0, False

        stmt = statements[i]
        if not (
            isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr)
        ):
            return [], 0, False

        expr = stmt.body[0].value
        if not (isinstance(expr, cst.Call) and isinstance(expr.func, cst.Attribute)):
            return [], 0, False

        # Only consider self/cls attribute calls
        func = expr.func
        if not (isinstance(func.value, cst.Name) and func.value.value in {"self", "cls"}):
            return [], 0, False

        # Build WithItem if this call maps to a known context (warns/raises/logs)
        with_item = build_with_item_from_assert_call(expr)
        if not with_item:
            return [], 0, False

        # Determine next statement (or None)
        next_stmt = statements[i + 1] if (i + 1) < len(statements) else None
        new_with, consumed = create_with_wrapping_next_stmt(with_item, next_stmt)
        return [new_with], consumed, True
    except Exception:
        # Conservative: do not handle on errors
        return [], 0, False


def transform_with_items(stmt: cst.With) -> tuple[cst.With, str | None, bool]:
    """Convert ``With.items`` that use ``self``/``cls`` assert helpers to pytest equivalents.

    This rewrites With items like ``with self.assertLogs(...):`` into
    ``with caplog.at_level(...):`` and similarly converts
    ``assertWarns``/``assertRaises`` items into ``pytest.warns``/
    ``pytest.raises``. The function returns a tuple ``(new_with,
    alias_name, changed)`` where ``alias_name`` is the first ``as``
    alias found on the original items (if any) and ``changed``
    indicates whether any item was transformed.

    Args:
        stmt: The original :class:`libcst.With` node.

    Returns:
        A tuple ``(new_with, alias_name, changed)``. ``new_with`` is the
        potentially rewritten With node; ``alias_name`` is an alias
        string or ``None``; ``changed`` is a boolean.
    """
    new_items: list[cst.WithItem] = []
    changed = False
    for item in stmt.items:
        ctx = item.item
        if isinstance(ctx, cst.Call) and isinstance(ctx.func, cst.Attribute):
            func = ctx.func
            if isinstance(func.value, cst.Name) and func.value.value in {"self", "cls"}:
                if func.attr.value in {"assertWarns", "assertWarnsRegex"}:
                    exc_arg = ctx.args[0] if ctx.args else None
                    match_arg = ctx.args[1] if len(ctx.args) >= 2 else None
                    warn_items_args_local: list[cst.Arg] = []
                    if exc_arg:
                        warn_items_args_local.append(cst.Arg(value=exc_arg.value))
                    if match_arg:
                        warn_items_args_local.append(cst.Arg(keyword=cst.Name(value="match"), value=match_arg.value))
                    warn_call = cst.Call(
                        func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="warns")),
                        args=warn_items_args_local,
                    )
                    new_item = cst.WithItem(item=warn_call)
                    new_items.append(new_item)
                    changed = True
                    continue

                if func.attr.value in {"assertLogs", "assertNoLogs"}:
                    caplog_level_args_local = get_caplog_level_args(ctx)
                    cap_call = cst.Call(
                        func=cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="at_level")),
                        args=caplog_level_args_local,
                    )
                    new_item = cst.WithItem(item=cap_call)
                    new_items.append(new_item)
                    changed = True
                    continue

                if func.attr.value in {"assertRaises", "assertRaisesRegex"}:
                    exc_arg = ctx.args[0] if ctx.args else None
                    raises_items_args_local: list[cst.Arg] = []
                    if exc_arg:
                        raises_items_args_local.append(cst.Arg(value=exc_arg.value))
                    raises_call = cst.Call(
                        func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="raises")),
                        args=raises_items_args_local,
                    )
                    new_item = cst.WithItem(item=raises_call, asname=item.asname)
                    new_items.append(new_item)
                    changed = True
                    continue

        new_items.append(item)

    if not changed:
        return stmt, None, False

    new_with = stmt.with_changes(items=new_items)

    alias_name = None
    for item in stmt.items:
        try:
            if item.asname and isinstance(item.asname, cst.AsName) and isinstance(item.asname.name, cst.Name):
                alias_name = item.asname.name.value
                break
        except Exception:
            pass

    return new_with, alias_name, True


def get_with_alias_name(items: list[cst.WithItem]) -> str | None:
    """Return the first ``as`` alias name from a list of With items.

    Args:
        items: Sequence of :class:`libcst.WithItem` nodes.

    Returns:
        The alias name string if an ``as`` name is present on any item,
        otherwise ``None``.
    """
    for item in items:
        try:
            if item.asname and isinstance(item.asname, cst.AsName) and isinstance(item.asname.name, cst.Name):
                return item.asname.name.value
        except Exception:
            pass
    return None


def rewrite_single_alias_assert(target_assert: cst.Assert, alias_name: str) -> cst.Assert | None:
    """Rewrite a single :class:`libcst.Assert` that references ``<alias>.output``.

    Many patterns produced by ``assertLogs``/``log`` aliases reference
    ``<alias>.output`` or other indexed access into the alias. This
    function attempts to rewrite membership and equality comparisons to
    use the ``caplog`` fixture (``caplog.records`` and
    ``caplog.records[index].getMessage()``) where appropriate.

    Args:
        target_assert: The :class:`libcst.Assert` node to rewrite.
        alias_name: The name of the alias (for example ``'log'``) to
            look for in attribute/subscript patterns.

    Returns:
        A new :class:`libcst.Assert` if a rewrite was applied, or
        ``None`` when no rewrite was possible.
    """
    try:
        t = target_assert.test

        # Helper: extract Attribute (alias.output) and list of Subscript slices from nested Subscript chains
        def _extract_attr_and_slices(
            expr: cst.BaseExpression,
        ) -> tuple[cst.Attribute | None, list[cst.SubscriptElement]]:
            slices: list[cst.SubscriptElement] = []
            cur = expr
            while isinstance(cur, cst.Subscript):
                slices.insert(0, cur.slice)
                cur = cur.value
            if isinstance(cur, cst.Attribute):
                return cast(cst.Attribute, cur), slices
            return None, []

        # Build caplog.records with the collected slices re-applied
        def _build_caplog_subscript(slices: list[cst.SubscriptElement]) -> cst.BaseExpression:
            base: cst.BaseExpression = cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="records"))
            for s in slices:
                base = cst.Subscript(value=cast(cst.BaseExpression, base), slice=s)
            return base

        # Quick fallback: if test is `UnaryOperation(expression=Comparison(...))`
        # try to rewrite the inner Comparison directly and preserve the UnaryOperation.
        if isinstance(t, cst.UnaryOperation) and isinstance(t.expression, cst.Comparison):
            inner_comp = t.expression
            try:
                # reuse comparison rewrite logic inline to avoid scoping issues
                # len(...) on left
                left = inner_comp.left
                if (
                    isinstance(left, cst.Call)
                    and isinstance(left.func, cst.Name)
                    and left.func.value == "len"
                    and left.args
                ):
                    arg0 = left.args[0].value
                    attr, slices = _extract_attr_and_slices(arg0)
                    if (
                        attr
                        and isinstance(attr.value, cst.Name)
                        and attr.value.value == alias_name
                        and isinstance(attr.attr, cst.Name)
                        and attr.attr.value == "output"
                    ):
                        new_arg = _build_caplog_subscript(slices)
                        new_left = left.with_changes(args=[cst.Arg(value=new_arg)])
                        new_comp = inner_comp.with_changes(left=new_left)
                        return target_assert.with_changes(test=t.with_changes(expression=new_comp))

                # membership and equality
                for comp in getattr(inner_comp, "comparisons", []):
                    if isinstance(comp.operator, cst.In):
                        comparator = comp.comparator
                        attr, slices = _extract_attr_and_slices(comparator)
                        if (
                            attr
                            and isinstance(attr.value, cst.Name)
                            and attr.value.value == alias_name
                            and isinstance(attr.attr, cst.Name)
                            and attr.attr.value == "output"
                        ):
                            new_sub = _build_caplog_subscript(slices)
                            getmsg = cst.Call(
                                func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")), args=[]
                            )
                            new_inner = inner_comp.with_changes(
                                comparisons=[cst.ComparisonTarget(operator=comp.operator, comparator=getmsg)]
                            )
                            return target_assert.with_changes(test=t.with_changes(expression=new_inner))

                # equality RHS/LHS
                def _eq_inline(node: cst.CSTNode) -> cst.CSTNode | None:
                    if isinstance(node, cst.Subscript):
                        attr, slices = _extract_attr_and_slices(node)
                        if (
                            attr
                            and isinstance(attr.value, cst.Name)
                            and attr.value.value == alias_name
                            and isinstance(attr.attr, cst.Name)
                            and attr.attr.value == "output"
                        ):
                            new_sub = _build_caplog_subscript(slices)
                            return cst.Call(
                                func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")), args=[]
                            )
                    if isinstance(node, cst.Attribute):
                        if (
                            isinstance(node.value, cst.Name)
                            and node.value.value == alias_name
                            and isinstance(node.attr, cst.Name)
                            and node.attr.value == "output"
                        ):
                            return cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="records"))
                    return None

                left_rewritten = _eq_inline(inner_comp.left)
                if left_rewritten is not None:
                    return target_assert.with_changes(
                        test=t.with_changes(expression=inner_comp.with_changes(left=left_rewritten))
                    )

                for ct in getattr(inner_comp, "comparisons", []):
                    if isinstance(ct.operator, cst.Equal):
                        rhs_rewritten = _eq_inline(ct.comparator)
                        if rhs_rewritten is not None:
                            new_comparisons = [cst.ComparisonTarget(operator=ct.operator, comparator=rhs_rewritten)]
                            return target_assert.with_changes(
                                test=t.with_changes(expression=inner_comp.with_changes(comparisons=new_comparisons))
                            )
            except Exception:
                pass

        # Try to rewrite a single Comparison expression; returns new Comparison or None
        def _rewrite_comparison_expr(comp_node: cst.Comparison) -> cst.Comparison | None:
            # len(alias.output...) pattern
            left = comp_node.left
            if (
                isinstance(left, cst.Call)
                and isinstance(left.func, cst.Name)
                and left.func.value == "len"
                and left.args
            ):
                arg0 = left.args[0].value
                attr, slices = _extract_attr_and_slices(arg0)
                if (
                    attr
                    and isinstance(attr.value, cst.Name)
                    and attr.value.value == alias_name
                    and isinstance(attr.attr, cst.Name)
                    and attr.attr.value == "output"
                ):
                    new_arg = _build_caplog_subscript(slices)
                    new_left = left.with_changes(args=[cst.Arg(value=new_arg)])
                    return comp_node.with_changes(left=new_left)

            # membership: 'x' in alias.output[...] pattern
            for comp in getattr(comp_node, "comparisons", []):
                if isinstance(comp.operator, cst.In):
                    comparator = comp.comparator
                    attr, slices = _extract_attr_and_slices(comparator)
                    if (
                        attr
                        and isinstance(attr.value, cst.Name)
                        and attr.value.value == alias_name
                        and isinstance(attr.attr, cst.Name)
                        and attr.attr.value == "output"
                    ):
                        new_sub = _build_caplog_subscript(slices)
                        getmsg = cst.Call(func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")), args=[])
                        return comp_node.with_changes(
                            comparisons=[cst.ComparisonTarget(operator=comp.operator, comparator=getmsg)]
                        )

            # equality comparisons: alias.output[...] == 'msg' or vice versa
            def _rewrite_eq_node(node: cst.CSTNode) -> cst.CSTNode | None:
                if isinstance(node, cst.Subscript):
                    attr, slices = _extract_attr_and_slices(node)
                    if (
                        attr
                        and isinstance(attr.value, cst.Name)
                        and attr.value.value == alias_name
                        and isinstance(attr.attr, cst.Name)
                        and attr.attr.value == "output"
                    ):
                        new_sub = _build_caplog_subscript(slices)
                        return cst.Call(func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")), args=[])
                if isinstance(node, cst.Attribute):
                    if (
                        isinstance(node.value, cst.Name)
                        and node.value.value == alias_name
                        and isinstance(node.attr, cst.Name)
                        and node.attr.value == "output"
                    ):
                        return cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="records"))
                return None

            left_rewritten = _rewrite_eq_node(comp_node.left)
            if left_rewritten is not None:
                return comp_node.with_changes(left=left_rewritten)

            for ct in getattr(comp_node, "comparisons", []):
                if isinstance(ct.operator, cst.Equal):
                    rhs_rewritten = _rewrite_eq_node(ct.comparator)
                    if rhs_rewritten is not None:
                        new_comparisons = [cst.ComparisonTarget(operator=ct.operator, comparator=rhs_rewritten)]
                        return comp_node.with_changes(comparisons=new_comparisons)

            return None

        # General recursive expression rewriter to support nested BooleanOperations,
        # ParenthesizedExpressions and UnaryOperations (e.g., `not (...)`).
        def rewrite_expr(expr: cst.BaseExpression) -> cst.BaseExpression | None:
            # Comparison nodes: try to rewrite using existing comparison logic
            if isinstance(expr, cst.Comparison):
                rewritten = _rewrite_comparison_expr(expr)
                return rewritten

            # BooleanOperation: recurse into left/right and rebuild if any side changes
            if isinstance(expr, cst.BooleanOperation):
                left = expr.left
                right = expr.right
                new_left = rewrite_expr(left)
                new_right = rewrite_expr(right)
                if new_left is not None or new_right is not None:
                    return expr.with_changes(
                        left=new_left if new_left is not None else left,
                        right=new_right if new_right is not None else right,
                    )
                return None

            # ParenthesizedExpression: recurse into inner expression
            if isinstance(expr, cst.ParenthesizedExpression):
                inner = expr.expression
                new_inner = rewrite_expr(inner)
                if new_inner is not None:
                    return expr.with_changes(expression=new_inner)
                return None

            # UnaryOperation: e.g., `not (<comparison>)`
            if isinstance(expr, cst.UnaryOperation):
                inner = expr.expression
                new_inner = rewrite_expr(inner)
                if new_inner is not None:
                    return expr.with_changes(expression=new_inner)
                return None

            return None

        # Unified UnaryOperation handling: the parser may produce either a
        # Comparison directly on `t.expression` (with lpar metadata) or a
        # ParenthesizedExpression wrapping a Comparison. Handle both shapes by
        # extracting the Comparison and attempting a membership/equality
        # rewrite against alias.output.
        def _try_unary_comparison_rewrite(unary: cst.UnaryOperation) -> cst.Assert | None:
            inner = unary.expression
            comp_node = None
            is_parenth = False
            if isinstance(inner, cst.Comparison):
                comp_node = inner
            elif isinstance(inner, cst.ParenthesizedExpression) and isinstance(inner.expression, cst.Comparison):
                comp_node = inner.expression
                is_parenth = True

            if comp_node is None:
                return None

            # Look for membership patterns: 'msg' in alias.output[...] -> getMessage()
            for ct in getattr(comp_node, "comparisons", []):
                if isinstance(ct.operator, cst.In):
                    comparator = ct.comparator
                    attr, slices = _extract_attr_and_slices(comparator)
                    if (
                        attr
                        and isinstance(attr.value, cst.Name)
                        and attr.value.value == alias_name
                        and isinstance(attr.attr, cst.Name)
                        and attr.attr.value == "output"
                    ):
                        new_sub = _build_caplog_subscript(slices)
                        getmsg = cst.Call(func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")), args=[])
                        new_comp = comp_node.with_changes(
                            comparisons=[cst.ComparisonTarget(operator=ct.operator, comparator=getmsg)]
                        )
                        if is_parenth:
                            new_inner = inner.with_changes(expression=new_comp)
                            new_unary = unary.with_changes(expression=new_inner)
                        else:
                            new_unary = unary.with_changes(expression=new_comp)
                        return target_assert.with_changes(test=new_unary)

            return None

        # Try to recursively rewrite the inner expression of a UnaryOperation
        # (e.g., `not <expr>`). This reuses `rewrite_expr` which understands
        # Comparison, BooleanOperation, ParenthesizedExpression and UnaryOperation
        # shapes and should cover nested boolean cases.
        if isinstance(t, cst.UnaryOperation):
            try:
                inner = t.expression
                new_inner = rewrite_expr(inner)
                if new_inner is not None:
                    new_unary = t.with_changes(expression=new_inner)
                    return target_assert.with_changes(test=new_unary)
            except Exception:
                # conservative: fall back to other explicit unary handlers below
                pass

            # Try the unary comparison-specific rewrite if recursive step didn't apply
            rewritten_unary = _try_unary_comparison_rewrite(t)
            if rewritten_unary is not None:
                return rewritten_unary

        # Handle case: UnaryOperation(expression=BooleanOperation(...)).
        # Recurse into the BooleanOperation's left/right sides and attempt to
        # rewrite any Comparison (or ParenthesizedExpression(Comparison)) that
        # targets alias.output. This covers patterns like:
        #   assert not (( 'err' in log.output[0]) and ('x' in log.output[1]))
        if isinstance(t, cst.UnaryOperation) and isinstance(t.expression, cst.BooleanOperation):
            bo = t.expression
            left = bo.left
            right = bo.right
            new_left = None
            new_right = None

            # Local helper: mirror the comparison rewrite logic for a single
            # Comparison node. This is slightly more permissive and will try
            # to rewrite len(...), membership and equality patterns that
            # reference alias.output.
            def rewrite_comp_manual(comp_node: cst.Comparison) -> cst.Comparison | None:
                try:
                    # len(alias.output...) pattern
                    left = comp_node.left
                    if (
                        isinstance(left, cst.Call)
                        and isinstance(left.func, cst.Name)
                        and left.func.value == "len"
                        and left.args
                    ):
                        arg0 = left.args[0].value
                        attr, slices = _extract_attr_and_slices(arg0)
                        if (
                            attr
                            and isinstance(attr.value, cst.Name)
                            and attr.value.value == alias_name
                            and isinstance(attr.attr, cst.Name)
                            and attr.attr.value == "output"
                        ):
                            new_arg = _build_caplog_subscript(slices)
                            new_left = left.with_changes(args=[cst.Arg(value=new_arg)])
                            return comp_node.with_changes(left=new_left)

                    # membership
                    for comp in getattr(comp_node, "comparisons", []):
                        if isinstance(comp.operator, cst.In):
                            comparator = comp.comparator
                            attr, slices = _extract_attr_and_slices(comparator)
                            if (
                                attr
                                and isinstance(attr.value, cst.Name)
                                and attr.value.value == alias_name
                                and isinstance(attr.attr, cst.Name)
                                and attr.attr.value == "output"
                            ):
                                new_sub = _build_caplog_subscript(slices)
                                getmsg = cst.Call(
                                    func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")), args=[]
                                )
                                return comp_node.with_changes(
                                    comparisons=[cst.ComparisonTarget(operator=comp.operator, comparator=getmsg)]
                                )

                    # equality LHS/RHS
                    def _rewrite_eq_node_local(node: cst.CSTNode) -> cst.CSTNode | None:
                        if isinstance(node, cst.Subscript):
                            attr, slices = _extract_attr_and_slices(node)
                            if (
                                attr
                                and isinstance(attr.value, cst.Name)
                                and attr.value.value == alias_name
                                and isinstance(attr.attr, cst.Name)
                                and attr.attr.value == "output"
                            ):
                                new_sub = _build_caplog_subscript(slices)
                                return cst.Call(
                                    func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")), args=[]
                                )
                        if isinstance(node, cst.Attribute):
                            if (
                                isinstance(node.value, cst.Name)
                                and node.value.value == alias_name
                                and isinstance(node.attr, cst.Name)
                                and node.attr.value == "output"
                            ):
                                return cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="records"))
                        return None

                    left_rewritten = _rewrite_eq_node_local(comp_node.left)
                    if left_rewritten is not None:
                        return comp_node.with_changes(left=left_rewritten)

                    for ct in getattr(comp_node, "comparisons", []):
                        if isinstance(ct.operator, cst.Equal):
                            rhs_rewritten = _rewrite_eq_node_local(ct.comparator)
                            if rhs_rewritten is not None:
                                new_comparisons = [cst.ComparisonTarget(operator=ct.operator, comparator=rhs_rewritten)]
                                return comp_node.with_changes(comparisons=new_comparisons)

                except Exception:
                    return None
                return None

            # Try to rewrite children using the explicit manual comparator rewriter
            new_left = None
            new_right = None
            if isinstance(left, cst.Comparison):
                new_left = rewrite_comp_manual(left)
            elif isinstance(left, cst.ParenthesizedExpression) and isinstance(left.expression, cst.Comparison):
                comp_new = rewrite_comp_manual(left.expression)
                if comp_new is not None:
                    new_left = left.with_changes(expression=comp_new)

            if isinstance(right, cst.Comparison):
                new_right = rewrite_comp_manual(right)
            elif isinstance(right, cst.ParenthesizedExpression) and isinstance(right.expression, cst.Comparison):
                comp_new = rewrite_comp_manual(right.expression)
                if comp_new is not None:
                    new_right = right.with_changes(expression=comp_new)

            if new_left is not None or new_right is not None:
                rebuilt = bo.with_changes(
                    left=new_left if new_left is not None else left, right=new_right if new_right is not None else right
                )
                new_unary = t.with_changes(expression=rebuilt)
                return target_assert.with_changes(test=new_unary)

        # Robustly handle UnaryOperation wrapping comparisons (e.g., `not (<comp>)`)
        if isinstance(t, cst.UnaryOperation):
            inner = t.expression
            # Unwrap parenthesis if present
            if isinstance(inner, cst.ParenthesizedExpression):
                inner_comp = inner.expression
                comp_new = _rewrite_comparison_expr(inner_comp) if isinstance(inner_comp, cst.Comparison) else None
                if comp_new is not None:
                    new_parenth = inner.with_changes(expression=comp_new)
                    new_unary = t.with_changes(expression=new_parenth)
                    return target_assert.with_changes(test=new_unary)
                # Fallback: try manual rebuild of Comparison by replacing targets referencing alias.output
                try:
                    changed = False
                    left = inner_comp.left
                    new_left = left
                    # len(...) on left
                    if (
                        isinstance(left, cst.Call)
                        and isinstance(left.func, cst.Name)
                        and left.func.value == "len"
                        and left.args
                    ):
                        arg0 = left.args[0].value
                        attr, slices = _extract_attr_and_slices(arg0)
                        if (
                            attr
                            and isinstance(attr.value, cst.Name)
                            and attr.value.value == alias_name
                            and isinstance(attr.attr, cst.Name)
                            and attr.attr.value == "output"
                        ):
                            new_arg = _build_caplog_subscript(slices)
                            new_left = left.with_changes(args=[cst.Arg(value=new_arg)])
                            changed = True

                    new_comps: list[cst.ComparisonTarget] = []
                    for ct in getattr(inner_comp, "comparisons", []):
                        op = ct.operator
                        comp = ct.comparator
                        # membership
                        if isinstance(op, cst.In):
                            attr, slices = _extract_attr_and_slices(comp)
                            if (
                                attr
                                and isinstance(attr.value, cst.Name)
                                and attr.value.value == alias_name
                                and isinstance(attr.attr, cst.Name)
                                and attr.attr.value == "output"
                            ):
                                new_sub = _build_caplog_subscript(slices)
                                getmsg = cst.Call(
                                    func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")), args=[]
                                )
                                new_comps.append(cst.ComparisonTarget(operator=op, comparator=getmsg))
                                changed = True
                                continue

                            # equality
                            if isinstance(op, cst.Equal):
                                # inline equality rewrite: if comparator is alias.output[...] rewrite to getMessage
                                rhs_rewritten = None
                                if isinstance(comp, cst.Subscript):
                                    a_attr, a_slices = _extract_attr_and_slices(comp)
                                    if (
                                        a_attr
                                        and isinstance(a_attr.value, cst.Name)
                                        and a_attr.value.value == alias_name
                                        and isinstance(a_attr.attr, cst.Name)
                                        and a_attr.attr.value == "output"
                                    ):
                                        new_sub = _build_caplog_subscript(a_slices)
                                        rhs_rewritten = cst.Call(
                                            func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")),
                                            args=[],
                                        )
                                elif isinstance(comp, cst.Attribute):
                                    if (
                                        isinstance(comp.value, cst.Name)
                                        and comp.value.value == alias_name
                                        and isinstance(comp.attr, cst.Name)
                                        and comp.attr.value == "output"
                                    ):
                                        rhs_rewritten = cst.Attribute(
                                            value=cst.Name(value="caplog"), attr=cst.Name(value="records")
                                        )

                                if rhs_rewritten is not None:
                                    new_comps.append(cst.ComparisonTarget(operator=op, comparator=rhs_rewritten))
                                    changed = True
                                    continue
                        # default: keep as-is
                        new_comps.append(ct)

                    if changed:
                        rebuilt = inner_comp.with_changes(left=new_left, comparisons=new_comps)
                        new_parenth = (
                            inner.with_changes(expression=rebuilt)
                            if isinstance(inner, cst.ParenthesizedExpression)
                            else rebuilt
                        )
                        new_unary = t.with_changes(expression=new_parenth)
                        return target_assert.with_changes(test=new_unary)
                except Exception:
                    pass
            else:
                comp_new = _rewrite_comparison_expr(inner) if isinstance(inner, cst.Comparison) else None
                if comp_new is not None:
                    new_unary = t.with_changes(expression=comp_new)
                    return target_assert.with_changes(test=new_unary)

        # Extra explicit fallback: sometimes the UnaryOperation wraps a
        # ParenthesizedExpression where the comparison uses `in` against
        # alias.output[...] and the direct path above may miss it. Handle
        # that specific shape here to ensure membership checks inside
        # parenthesized `not (...)` get rewritten to use caplog.getMessage().
        if isinstance(t, cst.UnaryOperation) and isinstance(t.expression, cst.ParenthesizedExpression):
            try:
                inner = t.expression
                inner_comp = inner.expression
                if isinstance(inner_comp, cst.Comparison):
                    for comp in getattr(inner_comp, "comparisons", []):
                        if isinstance(comp.operator, cst.In):
                            comparator = comp.comparator
                            attr, slices = _extract_attr_and_slices(comparator)
                            if (
                                attr
                                and isinstance(attr.value, cst.Name)
                                and attr.value.value == alias_name
                                and isinstance(attr.attr, cst.Name)
                                and attr.attr.value == "output"
                            ):
                                new_sub = _build_caplog_subscript(slices)
                                getmsg = cst.Call(
                                    func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")),
                                    args=[],
                                )
                                new_inner = inner_comp.with_changes(
                                    comparisons=[cst.ComparisonTarget(operator=comp.operator, comparator=getmsg)]
                                )
                                new_parenth = inner.with_changes(expression=new_inner)
                                new_unary = t.with_changes(expression=new_parenth)
                                return target_assert.with_changes(test=new_unary)
            except Exception:
                # conservative: ignore and continue
                pass

        # Attempt a general rewrite of the test expression
        new_test = rewrite_expr(t)
        if new_test is not None:
            return target_assert.with_changes(test=new_test)

        # Handle case where UnaryOperation.expression is a Comparison that
        # carries parenthesis information (e.g., parsed as Comparison with
        # lpar/rpar). This shape can appear for `not ( ... )` but where the
        # parser attached parentheses onto the Comparison node rather than
        # creating a ParenthesizedExpression. Detect that and try to rewrite
        # membership targets referencing alias.output.
        if (
            isinstance(t, cst.UnaryOperation)
            and isinstance(t.expression, cst.Comparison)
            and getattr(t.expression, "lpar", None)
        ):
            inner_comp = t.expression
            try:
                for comp in getattr(inner_comp, "comparisons", []):
                    if isinstance(comp.operator, cst.In):
                        comparator = comp.comparator
                        attr, slices = _extract_attr_and_slices(comparator)
                        if (
                            attr
                            and isinstance(attr.value, cst.Name)
                            and attr.value.value == alias_name
                            and isinstance(attr.attr, cst.Name)
                            and attr.attr.value == "output"
                        ):
                            new_sub = _build_caplog_subscript(slices)
                            getmsg = cst.Call(
                                func=cst.Attribute(value=new_sub, attr=cst.Name(value="getMessage")), args=[]
                            )
                            new_inner = inner_comp.with_changes(
                                comparisons=[cst.ComparisonTarget(operator=comp.operator, comparator=getmsg)]
                            )
                            new_unary = t.with_changes(expression=new_inner)
                            return target_assert.with_changes(test=new_unary)
            except Exception:
                pass

        # Single Comparison fallback
        if isinstance(t, cst.Comparison):
            comp_new = _rewrite_comparison_expr(t)
            if comp_new is not None:
                return target_assert.with_changes(test=comp_new)

        return None
    except Exception:
        # Conservative: do not rewrite on any unexpected errors
        return None


def rewrite_asserts_using_alias_in_with_body(new_with: cst.With, alias_name: str) -> cst.With:
    """Rewrite asserts inside a With block that reference a log alias.

    Given a :class:`libcst.With` that originally used ``with
    something as <alias>``, this scans the with-body and rewrites any
    bare ``assert`` expressions or single-line ``assert`` statements
    that reference ``<alias>.output`` to instead use the ``caplog``
    fixture equivalents.

    Args:
        new_with: The :class:`libcst.With` node to transform.
        alias_name: The alias name to search for (for example ``'log'``).

    Returns:
        The potentially rewritten :class:`libcst.With` node. On any
        error the original node is returned unchanged.
    """
    try:
        new_body: list[cst.BaseSmallStatement] = []
        for inner in getattr(new_with.body, "body", []):
            s = inner
            # Try rewriting bare Assert nodes
            if isinstance(s, cst.Assert):
                rewritten = rewrite_single_alias_assert(s, alias_name)
                new_body.append(rewritten if rewritten is not None else s)
                continue

            # Try rewriting SimpleStatementLine wrapping an Assert
            if isinstance(s, cst.SimpleStatementLine) and len(s.body) == 1 and isinstance(s.body[0], cst.Assert):
                rewritten = rewrite_single_alias_assert(s.body[0], alias_name)
                new_body.append(s.with_changes(body=[rewritten]) if rewritten is not None else s)
                continue

            # Default: keep original statement
            new_body.append(s)

        new_block = new_with.body.with_changes(body=new_body)
        return new_with.with_changes(body=new_block)
    except Exception:
        # Conservative: return original when any error occurs
        return new_with


def rewrite_following_statements_for_alias(
    statements: list[cst.BaseStatement], start_index: int, alias_name: str, look_ahead: int = 12
) -> None:
    """Rewrite subsequent statements that reference a With alias to use caplog.

    After converting a ``with ... as <alias>`` to a pytest-compatible
    with, callers may want to also rewrite a small number of following
    statements that still reference the original alias. This helper
    inspects ``statements`` in-place starting at ``start_index`` and
    attempts to rewrite up to ``look_ahead`` statements that are
    assertions referencing ``<alias>.output``.

    The function updates the ``statements`` list in-place and is
    intentionally conservative: exceptions are caught and ignored so
    callers can continue safely.
    """
    for k in range(start_index, min(len(statements), start_index + look_ahead)):
        s = statements[k]
        try:
            target_assert = None
            wrapper_stmt = None
            if isinstance(s, cst.Assert):
                target_assert = s
            elif isinstance(s, cst.SimpleStatementLine) and len(s.body) == 1 and isinstance(s.body[0], cst.Assert):
                wrapper_stmt = s
                target_assert = s.body[0]

            if target_assert is None:
                continue

            rewritten = rewrite_single_alias_assert(target_assert, alias_name)
            if rewritten is not None:
                if wrapper_stmt is not None:
                    statements[k] = wrapper_stmt.with_changes(body=[rewritten])
                else:
                    statements[k] = cst.SimpleStatementLine(body=[rewritten])
        except Exception:
            # Conservative: do not handle on errors
            pass


def wrap_assert_in_block(statements: list[cst.BaseStatement]) -> list[cst.BaseStatement]:
    """Convert standalone unittest assert-context calls into With blocks.

    This helper looks for bare expression statements like
    ``self.assertLogs(...)`` or existing ``with self.assertLogs(...)``
    blocks and rewrites them to use pytest-style context managers such
    as ``caplog.at_level(...)`` or ``pytest.raises(...)``. The
    function returns a new list of statements with the transformations
    applied; input ordering is preserved when nodes are not changed.

    Args:
        statements: The list of :class:`libcst.BaseStatement` nodes to
            process.

    Returns:
        A new list of statements with applicable transformations
        applied. The function is conservative and preserves original
        nodes on error.
    """
    out: list[cst.BaseStatement] = []
    i = 0
    while i < len(statements):
        stmt = statements[i]
        wrapped = False

        # Handle bare expression calls like: self.assertLogs(...)
        if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
            try:
                nodes_to_append, consumed, handled = handle_bare_assert_call(statements, i)
            except Exception:
                # be conservative on errors and fall back to original behavior
                nodes_to_append, consumed, handled = ([], 0, False)

            if handled:
                out.extend(nodes_to_append)
                i += consumed
                wrapped = consumed > 0

        # Handle existing with-statements that use self.assertLogs / assertWarns etc.
        elif isinstance(stmt, cst.With):
            try:
                new_items: list[cst.WithItem] = []
                changed = False
                for item in stmt.items:
                    ctx = item.item
                    if isinstance(ctx, cst.Call) and isinstance(ctx.func, cst.Attribute):
                        func = ctx.func
                        if isinstance(func.value, cst.Name) and func.value.value in {"self", "cls"}:
                            if func.attr.value in {"assertWarns", "assertWarnsRegex"}:
                                exc_arg = ctx.args[0] if ctx.args else None
                                match_arg = ctx.args[1] if len(ctx.args) >= 2 else None
                                warn_items_args_local: list[cst.Arg] = []
                                if exc_arg:
                                    warn_items_args_local.append(cst.Arg(value=exc_arg.value))
                                if match_arg:
                                    warn_items_args_local.append(
                                        cst.Arg(keyword=cst.Name(value="match"), value=match_arg.value)
                                    )
                                warn_call = cst.Call(
                                    func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="warns")),
                                    args=warn_items_args_local,
                                )
                                new_item = cst.WithItem(item=warn_call)
                                new_items.append(new_item)
                                changed = True
                                continue

                            if func.attr.value in {"assertLogs", "assertNoLogs"}:
                                # logger_arg intentionally unused here; we only need level
                                level_arg = ctx.args[1] if len(ctx.args) >= 2 else None
                                if level_arg is None:
                                    for a in ctx.args:
                                        if a.keyword and isinstance(a.keyword, cst.Name) and a.keyword.value == "level":
                                            level_arg = a
                                            break
                                caplog_level_args_local: list[cst.Arg] = []
                                if level_arg:
                                    level_value = level_arg.value if isinstance(level_arg, cst.Arg) else level_arg.value
                                    caplog_level_args_local.append(cst.Arg(value=level_value))
                                else:
                                    caplog_level_args_local.append(cst.Arg(value=cst.SimpleString(value='"INFO"')))
                                cap_call = build_caplog_call(ctx)
                                # Do not preserve `as <name>` alias for caplog conversions;
                                # tests expect use of the `caplog` fixture rather than a
                                # local alias variable.
                                new_item = cst.WithItem(item=cap_call)
                                new_items.append(new_item)
                                changed = True
                                continue

                            if func.attr.value in {"assertRaises", "assertRaisesRegex"}:
                                exc_arg = ctx.args[0] if ctx.args else None
                                raises_items_args_local: list[cst.Arg] = []
                                if exc_arg:
                                    raises_items_args_local.append(cst.Arg(value=exc_arg.value))
                                raises_call = cst.Call(
                                    func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="raises")),
                                    args=raises_items_args_local,
                                )
                                # Preserve any 'as <name>' alias from the original WithItem
                                new_item = cst.WithItem(item=raises_call, asname=item.asname)
                                new_items.append(new_item)
                                changed = True
                                continue

                    # default: keep original item
                    new_items.append(item)

                if changed:
                    new_with = stmt.with_changes(items=new_items)

                    # If the original WithItem had an alias (e.g., 'as log'),
                    # rewrite references to that alias inside the WITH block to
                    # use the `caplog` fixture. This covers patterns like
                    #   assert len(log.output) == 2
                    #   assert 'msg' in log.output[0]
                    # and also unittest-style calls inside the block such as
                    #   self.assertEqual(len(log.output), 2)
                    alias_name = get_with_alias_name(stmt.items)

                    if alias_name:
                        try:
                            new_with = rewrite_asserts_using_alias_in_with_body(new_with, alias_name)
                        except Exception:
                            # conservative: on any failure keep original new_with
                            pass

                    # Always append the transformed With node (changed -> append)
                    out.append(new_with)

                    # If the original WithItem had an alias (e.g., 'as log'), we need to
                    # rewrite following assertions that reference that alias to use
                    # the `caplog` fixture. For example:
                    #   assert len(log.output) == 2  ->  assert len(caplog.records) == 2
                    #   assert 'msg' in log.output[0] -> assert 'msg' in caplog.records[0].getMessage()
                    alias_name = get_with_alias_name(stmt.items)

                    if alias_name:
                        try:
                            rewrite_following_statements_for_alias(statements, i + 1, alias_name)
                        except Exception:
                            # conservative: on any error do nothing
                            pass

                    i += 1
                    wrapped = True
            except Exception:
                # Fall back to preserving original with-statement
                pass

        if not wrapped:
            out.append(stmt)
            i += 1

    return out


def transform_skip_test(node: cst.Call) -> cst.CSTNode:
    """Convert ``self.skipTest(...)`` to ``pytest.skip(...)``.

    Preserves any positional or keyword arguments supplied to the
    original call.
    """
    # Preserve any arguments (message or reason)
    new_func = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="skip"))
    return cst.Call(func=new_func, args=node.args)


def transform_fail(node: cst.Call) -> cst.CSTNode:
    """Convert ``self.fail(...)`` to ``pytest.fail(...)``.

    All arguments are preserved.
    """
    # Use a Name with dotted path parsed as Name; better to use Attribute
    new_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fail"))
    return cst.Call(func=new_attr, args=node.args)


def transform_assert_dict_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertDictEqual(a, b)`` to ``assert a == b``.

    Returns a :class:`libcst.Assert` performing equality when two
    positional arguments are present; otherwise returns the original
    node.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_caplog_alias_string_fallback(code: str) -> str:
    """Apply conservative string-level fixes for caplog alias patterns.

    Some patterns are difficult to rewrite reliably using only libcst
    transforms. This helper applies a few safe, regex-based
    substitutions to convert occurrences of ``<alias>.output`` to
    ``caplog.records`` and to call ``.getMessage()`` when comparisons or
    membership checks expect a message string.

    Args:
        code: The source code string to operate on.

    Returns:
        The modified source string after performing the conservative
        substitutions.
    """
    import re

    out = code
    # Replace direct alias.output[...] with caplog.records[...]
    out = re.sub(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.output\s*\[", r"caplog.records[", out)
    # Replace standalone alias.output (no subscript) with caplog.records (e.g., len(log.output))
    out = re.sub(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.output\b", r"caplog.records", out)

    # If someone compared caplog.records[0] == 'msg', rewrite to caplog.records[0].getMessage() == 'msg'
    out = re.sub(r"caplog\.records\s*\[(\d+)\]\s*==\s*('.*?'|\".*?\")", r"caplog.records[\1].getMessage() == \2", out)

    # Membership: 'msg' in caplog.records[0] -> 'msg' in caplog.records[0].getMessage()
    out = re.sub(r"('.*?'|\".*?\")\s*in\s*caplog\.records\s*\[(\d+)\]", r"\1 in caplog.records[\2].getMessage()", out)

    return out


def transform_assert_list_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertListEqual(a, b)`` to ``assert a == b``.

    Returns a :class:`libcst.Assert` when two positional arguments are
    provided; otherwise returns the input node unchanged.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_set_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertSetEqual(a, b)`` to ``assert a == b``.

    Returns a :class:`libcst.Assert` when two positional arguments are
    provided; otherwise returns the input node unchanged.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_tuple_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertTupleEqual(a, b)`` to ``assert a == b``.

    Returns a :class:`libcst.Assert` when two positional arguments are
    provided; otherwise returns the input node unchanged.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_greater(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertGreater(a, b)`` to ``assert a > b``.

    Returns a :class:`libcst.Assert` performing the greater-than
    comparison when two positional arguments are provided.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.GreaterThan(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_greater_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertGreaterEqual(a, b)`` to ``assert a >= b``.

    Returns a :class:`libcst.Assert` performing the greater-or-equal
    comparison when two positional arguments are provided.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.GreaterThanEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_less(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertLess(a, b)`` to ``assert a < b``.

    Returns a :class:`libcst.Assert` performing the less-than
    comparison when two positional arguments are provided.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.LessThan(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_less_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertLessEqual(a, b)`` to ``assert a <= b``.

    Returns a :class:`libcst.Assert` performing the less-or-equal
    comparison when two positional arguments are provided.
    """
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.LessThanEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_almost_equal(node: cst.Call) -> cst.CSTNode:
    """Rewrite ``self.assertAlmostEqual(a, b[, places=N])`` to ``assert a == pytest.approx(b)`` or a ``round`` fallback.

    When ``places`` is omitted this helper prefers ``pytest.approx(b)``
    which is the common pytest idiom. If ``places`` is supplied the
    function falls back to a ``round(a - b, places) == 0`` style
    comparison to preserve the original semantic intent.

    Args:
        node: The original :class:`libcst.Call` node.

    Returns:
        A :class:`libcst.Assert` node implementing the approximation
        when two positional arguments are present. If only one or zero
        positional args are present the function returns ``None`` or the
        original node (preserving conservative behavior).
    """
    if len(node.args) >= 2:
        left = node.args[0].value
        right = node.args[1].value
        # find places kwarg if present (libcst represents keywords as Arg with keyword attr)
        places = None
        for arg in node.args:
            if arg.keyword and isinstance(arg.keyword, cst.Name) and arg.keyword.value == "places":
                places = arg.value
                break
        # If places not provided, use pytest.approx(right)
        if places is None:
            approx_call = cst.Call(
                func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="approx")),
                args=[cst.Arg(value=right)],
            )
            comp = cst.Comparison(
                left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=approx_call)]
            )
            return cst.Assert(test=comp)
        else:
            # Fallback: keep previous behavior using round() to emulate places
            diff = cst.BinaryOperation(left=left, operator=cst.Subtract(), right=right)
            round_call = cst.Call(func=cst.Name(value="round"), args=[cst.Arg(value=diff), cst.Arg(value=places)])
            comp = cst.Comparison(
                left=round_call,
                comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer(value="0"))],
            )
            return cst.Assert(test=comp)


def transform_assert_almost_equals(node: cst.Call) -> cst.CSTNode:
    """Alias shim for the deprecated ``assertAlmostEquals`` name.

    Delegates to :func:`transform_assert_almost_equal` to perform the
    same rewrite.
    """
    return transform_assert_almost_equal(node)


def transform_assert_not_almost_equals(node: cst.Call) -> cst.CSTNode:
    """Alias shim for the deprecated ``assertNotAlmostEquals`` name.

    Delegates to :func:`transform_assert_not_almost_equal`.
    """
    return transform_assert_not_almost_equal(node)
