"""Assertion transformation helpers extracted from unittest_transformer.

These functions perform CST-based conversion of unittest assertion calls
into equivalent pytest-style assertions or expressions. They are
extracted to keep `unittest_transformer.py` focused and allow reuse.

Note on parser shapes and conservative rewrites
---------------------------------------------
The Python parser (libcst) can express semantically-equivalent source
in multiple CST shapes. In particular, code that looks like

        assert not ('err' in log.output[0])

may be parsed as any of the following shapes in practice:

- a direct :class:`libcst.Comparison` node
- a :class:`libcst.ParenthesizedExpression` wrapping a
    :class:`libcst.Comparison`
- a :class:`libcst.Comparison` node that carries left/right parenthesis
    metadata
- a :class:`libcst.BooleanOperation` combining multiple
    :class:`libcst.Comparison` children (``and``/``or``)
- a :class:`libcst.UnaryOperation` (``not``) whose ``expression`` is any
    of the above

The helpers in this module (for example ``rewrite_single_alias_assert``,
``_extract_attr_and_slices`` and ``_build_caplog_subscript``) are
implemented to handle the common shapes above by: (1) attempting to
rewrite inner ``Comparison`` nodes, (2) walking into
``ParenthesizedExpression``/``UnaryOperation`` wrappers, and (3)
recursively visiting ``BooleanOperation`` children. Rewrites are
conservative — if a shape or child expression is not recognized, the
helper will return ``None`` (no rewrite) so the original code is left
unchanged. This keeps transformations safe and minimizes false
positives during large-scale automated migrations.

If you add additional rewrite logic, prefer returning ``None`` rather
than producing a best-effort transformation when the input shape is
ambiguous.
"""

from typing import cast

import libcst as cst


def transform_assert_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_almost_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertNotAlmostEqual(a, b, places=N) -> assert not round(a-b, places) == 0."""
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
    """Transform assertTrue to assert."""
    if len(node.args) >= 1:
        return cst.Assert(test=node.args[0].value)
    return node


def transform_assert_false(node: cst.Call) -> cst.CSTNode:
    """Transform assertFalse to assert not."""
    if len(node.args) >= 1:
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=node.args[0].value))
    return node


def transform_assert_is(node: cst.Call) -> cst.CSTNode:
    """Transform assertIs to assert is."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertNotEqual to assert !=."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.NotEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_not(node: cst.Call) -> cst.CSTNode:
    """Transform assertIsNot to assert is not."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_none(node: cst.Call) -> cst.CSTNode:
    """Transform assertIsNone to assert <expr> is None."""
    if len(node.args) >= 1:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=cst.Name(value="None"))],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_not_none(node: cst.Call) -> cst.CSTNode:
    """Transform assertIsNotNone to assert <expr> is not None."""
    if len(node.args) >= 1:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name(value="None"))],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_in(node: cst.Call) -> cst.CSTNode:
    """Transform assertNotIn to assert not in."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.NotIn(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_isinstance(node: cst.Call) -> cst.CSTNode:
    """Transform assertIsInstance(obj, cls) -> assert isinstance(obj, cls)."""
    if len(node.args) >= 2:
        isinstance_call = cst.Call(
            func=cst.Name(value="isinstance"),
            args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
        )
        return cst.Assert(test=isinstance_call)
    return node


def transform_assert_not_isinstance(node: cst.Call) -> cst.CSTNode:
    """Transform assertNotIsInstance(obj, cls) -> assert not isinstance(obj, cls)."""
    if len(node.args) >= 2:
        isinstance_call = cst.Call(
            func=cst.Name(value="isinstance"),
            args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
        )
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=isinstance_call))
    return node


def transform_assert_count_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertCountEqual(a, b) -> assert sorted(a) == sorted(b)."""
    if len(node.args) >= 2:
        left = cst.Call(func=cst.Name(value="sorted"), args=[cst.Arg(value=node.args[0].value)])
        right = cst.Call(func=cst.Name(value="sorted"), args=[cst.Arg(value=node.args[1].value)])
        comp = cst.Comparison(left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=right)])
        return cst.Assert(test=comp)
    return node


def transform_assert_multiline_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertMultiLineEqual(a, b) -> assert a == b."""
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
    """Transform assertRegex(a, pattern) -> assert re.search(pattern, a).

    This is a simple approximation and will require `re` to be available.
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
    """Transform assertNotRegex(a, pattern) -> assert not re.search(pattern, a)."""
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
    """Transform assertIn to assert in."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_raises(node: cst.Call) -> cst.CSTNode:
    """Transform assertRaises to pytest.raises context manager (approximate)."""
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
    """Transform assertRaisesRegex(exc, callable, regex) -> pytest.raises(exc, match=regex)."""
    # Only transform when at least 3 args are provided: (exc, callable, regex)
    if len(node.args) >= 3:
        exc = node.args[0].value
        match_arg = node.args[2].value
        args: list[cst.Arg] = [cst.Arg(value=exc)]
        args.append(cst.Arg(keyword=cst.Name(value="match"), value=match_arg))
        return cst.Call(func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="raises")), args=args)
    return node


def get_self_attr_call(stmt: cst.BaseStatement) -> tuple[str, cst.Call] | None:
    """If `stmt` is a bare expression like `self.foo(...)` or `cls.foo(...)`,
    return (attr_name, call_expr). Otherwise return None.
    """
    if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
        expr = stmt.body[0].value
        if isinstance(expr, cst.Call) and isinstance(expr.func, cst.Attribute):
            func = expr.func
            if isinstance(func.value, cst.Name) and func.value.value in {"self", "cls"}:
                return func.attr.value, expr
    return None


def get_caplog_level_args(call_expr: cst.Call) -> list[cst.Arg]:
    """Extract caplog.at_level args from an `assertLogs`/`assertNoLogs` call.

    Returns a list of `cst.Arg` suitable for use as the args of `caplog.at_level(...)`.
    If no level is provided, defaults to `"INFO"`.
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
    """Build a `caplog.at_level(...)` Call node from an `assertLogs`/`assertNoLogs` call expression.

    Uses `get_caplog_level_args` internally. Always returns a `cst.Call` whose
    func is `caplog.at_level` and whose args default to '"INFO"' when missing.
    """
    args = get_caplog_level_args(call_expr)
    return cst.Call(func=cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="at_level")), args=args)


def build_with_item_from_assert_call(call_expr: cst.Call) -> cst.WithItem | None:
    """Given a Call node whose func is a `self`/`cls` attribute, build
    a corresponding pytest WithItem for known assert context managers.

    Returns a `WithItem` or None if the call_expr is not one we transform.
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
    """Create a `With` node that uses `with_item` and wraps `next_stmt`.

    Returns a tuple (with_node, consumed_count) where consumed_count is 2
    when a following statement was wrapped (original code advanced i by 2),
    or 1 when only the assert-call line was consumed and a `pass` body is used.
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
    """Handle a bare SimpleStatementLine like `self.assertLogs(...)` or `self.assertRaises(...)`.

    Returns (nodes_to_append, consumed_count, handled).
    This reuses existing helpers: `build_with_item_from_assert_call` and `create_with_wrapping_next_stmt`.
    If the stmt is not a matching bare assert call it returns ([], 0, False).
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
    """Rewrite With.items that reference `self`/`cls` attribute calls into pytest equivalents.

    Returns (new_with, alias_name, changed) where alias_name is the value of an
    `as` alias if present on any original WithItem, or None.
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
    """Return the alias name used in a With.items list (e.g., the `as name`).

    Returns the first alias name found or None.
    """
    for item in items:
        try:
            if item.asname and isinstance(item.asname, cst.AsName) and isinstance(item.asname.name, cst.Name):
                return item.asname.name.value
        except Exception:
            pass
    return None


def rewrite_single_alias_assert(target_assert: cst.Assert, alias_name: str) -> cst.Assert | None:
    """Rewrite a single `assert` node that references `alias_name.output`.

    Returns a rewritten `cst.Assert` or None if no rewrite was applicable.
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
    """Look through a With block body and rewrite assert statements that reference alias_name.output.

    Returns a possibly rewritten `With` node.
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
    """Look ahead after a With block and rewrite any asserts that reference the alias.

    This updates the `statements` list in place. It is conservative and catches
    exceptions so as not to break transformation on errors.
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
    """Wrap `self.assertLogs`/`self.assertNoLogs` calls followed by a statement into a With block.

    This mirrors the previous in-transformer behavior moved here so it can be reused
    by both CST and string-based pipelines.
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
    """Transform self.skipTest(msg) into pytest.skip(msg)."""
    # Preserve any arguments (message or reason)
    new_func = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="skip"))
    return cst.Call(func=new_func, args=node.args)


def transform_fail(node: cst.Call) -> cst.CSTNode:
    """Transform self.fail(msg) into pytest.fail(msg)."""
    # Use a Name with dotted path parsed as Name; better to use Attribute
    new_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fail"))
    return cst.Call(func=new_attr, args=node.args)


def transform_assert_dict_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertDictEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_caplog_alias_string_fallback(code: str) -> str:
    """Conservative string-level rewrites to fix caplog/alias patterns missed by CST transforms.

    This function applies a few safe regex-based replacements to convert
    `log.output` patterns to `caplog.records` and to call `.getMessage()`
    where membership/equality comparisons expect message strings.
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
    """Transform assertListEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_set_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertSetEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_tuple_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertTupleEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_greater(node: cst.Call) -> cst.CSTNode:
    """Transform assertGreater(a, b) -> assert a > b."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.GreaterThan(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_greater_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertGreaterEqual(a, b) -> assert a >= b."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.GreaterThanEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_less(node: cst.Call) -> cst.CSTNode:
    """Transform assertLess(a, b) -> assert a < b."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.LessThan(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_less_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertLessEqual(a, b) -> assert a <= b."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.LessThanEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_almost_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertAlmostEqual(a, b, places=N) -> assert a == pytest.approx(b, rel=None, abs=...) or use approx with places.

    We'll prefer pytest.approx(b) for simple forms. If `places` is provided we'll approximate using a small absolute tolerance via round/places fallback.
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
    """Alias for deprecated assertAlmostEquals -> delegate to transform_assert_almost_equal."""
    return transform_assert_almost_equal(node)


def transform_assert_not_almost_equals(node: cst.Call) -> cst.CSTNode:
    """Alias for deprecated assertNotAlmostEquals -> delegate to transform_assert_not_almost_equal."""
    return transform_assert_not_almost_equal(node)
