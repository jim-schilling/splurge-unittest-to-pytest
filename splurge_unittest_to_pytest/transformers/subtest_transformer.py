"""Helpers to transform unittest subTest patterns to pytest equivalents.

This module provides conservative, small helpers that inspect and rewrite
``with self.subTest(...)`` patterns. Functions include utilities to:

- Convert a simple ``for`` loop containing ``with self.subTest(...)``
    into a ``@pytest.mark.parametrize`` decorator when it is safe to do so.
- Convert ``self.subTest`` uses into calls to the lightweight
    ``subtests.test`` helper (when present) by rewriting ``with`` items.
- Detect whether a body already uses the ``subtests`` helper.

All transforms are intentionally cautious: when a pattern is ambiguous
or potentially unsafe to rewrite the helpers will return ``None`` or
leave nodes unchanged.
"""

# mypy: ignore-errors

from __future__ import annotations

from collections.abc import Sequence

import libcst as cst


def _extract_from_list_or_tuple(node: cst.BaseExpression) -> list[cst.BaseExpression] | None:
    """Return list of element expressions when node is a List or Tuple.

    Args:
        node: A :class:`libcst.BaseExpression` expected to be a list or
            tuple literal.

    Returns:
        A list of :class:`libcst.BaseExpression` values when ``node`` is a
        :class:`libcst.List` or :class:`libcst.Tuple`, otherwise ``None``.
    """

    vals: list[cst.BaseExpression] = []
    if isinstance(node, cst.List | cst.Tuple):
        for el in node.elements:
            if isinstance(el, cst.Element):
                vals.append(el.value)
        return vals
    return None


def convert_simple_subtests_to_parametrize(
    original_func: cst.FunctionDef, updated_func: cst.FunctionDef, transformer
) -> cst.FunctionDef | None:
    """Attempt to convert a simple ``for: with self.subTest(...)`` to parametrize.

    This function performs a conservative set of checks to determine if
    the body of ``updated_func`` contains a single ``for`` loop whose
    body is a single ``with self.subTest(...)`` block and where the
    iteration values can be statically determined (a literal list/tuple
    or a small ``range`` literal). When those conditions are met it
    builds a ``@pytest.mark.parametrize`` decorator and returns a
    modified function definition with the new decorator and the inner
    subTest body as the function body.

    Args:
        original_func: The original :class:`libcst.FunctionDef` prior to
            other rewrites (unused by this helper but provided for
            context).
        updated_func: The :class:`libcst.FunctionDef` to analyze and
            potentially transform.
        transformer: Transformer instance used to record transformation
            side-effects (for example setting
            ``transformer.needs_pytest_import = True``).

    Returns:
        A new :class:`libcst.FunctionDef` with a ``parametrize`` decorator
        when the conversion is safe, otherwise ``None``.
    """
    try:
        body_stmts = list(updated_func.body.body)
        if len(body_stmts) == 0:
            return None

        # find the first for-loop in the function body (may not be the very first stmt)
        first = None
        first_index = -1
        for i, stmt in enumerate(body_stmts):
            if isinstance(stmt, cst.For):
                first = stmt
                first_index = i
                break
        if first is None:
            return None

        for_body = first.body
        if not isinstance(for_body, cst.IndentedBlock) or len(for_body.body) != 1:
            return None
        inner = for_body.body[0]
        if not isinstance(inner, cst.With):
            return None

        if len(inner.items) != 1:
            return None
        call = inner.items[0].item
        if not isinstance(call, cst.Call) or not isinstance(call.func, cst.Attribute):
            return None
        if not isinstance(call.func.value, cst.Name) or call.func.value.value not in {"self", "cls"}:
            return None
        if call.func.attr.value != "subTest":
            return None

        if len(call.args) != 1:
            return None

        single_arg = call.args[0]
        if single_arg.keyword is None:
            arg_expr = single_arg.value
            if not isinstance(arg_expr, cst.Name):
                return None
            param_name = arg_expr.value
        else:
            if not isinstance(single_arg.keyword, cst.Name):
                return None
            kw_name = single_arg.keyword.value
            arg_expr = single_arg.value
            if not isinstance(arg_expr, cst.Name):
                return None
            if not isinstance(first.target, cst.Name) or arg_expr.value != first.target.value:
                return None
            param_name = kw_name

        inner_body = inner.body
        if not isinstance(inner_body, cst.IndentedBlock) or len(inner_body.body) < 1:
            return None
        for stmt in inner_body.body:
            # Allow an If block.
            if isinstance(stmt, cst.If):
                continue
            # Allow a single simple small-statement as long as it is not a Return.
            if isinstance(stmt, cst.SimpleStatementLine):
                if len(stmt.body) != 1:
                    return None
                inner_stmt = stmt.body[0]
                # Disallow Return statements inside the subTest body because
                # they make the conversion unsafe.
                if isinstance(inner_stmt, cst.Return):
                    return None
                # otherwise accept (Expr, Assign, Assert, etc.)
                continue
            # other statement types are not allowed
            return None

        iter_node = first.iter
        values: list[cst.BaseExpression] = []

        maybe_vals = _extract_from_list_or_tuple(iter_node)
        if maybe_vals is not None:
            values = maybe_vals
        else:
            # range(...) with literal integer args
            if (
                isinstance(iter_node, cst.Call)
                and isinstance(iter_node.func, cst.Name)
                and iter_node.func.value == "range"
            ):
                ok = True
                args_vals: list[int] = []
                for a in iter_node.args:
                    if isinstance(a.value, cst.Integer):
                        try:
                            args_vals.append(int(a.value.value))
                        except Exception:
                            ok = False
                            break
                    else:
                        ok = False
                        break
                if ok and len(args_vals) in {1, 2, 3}:
                    try:
                        if len(args_vals) == 1:
                            start, stop, step = 0, args_vals[0], 1
                        elif len(args_vals) == 2:
                            start, stop = args_vals[0], args_vals[1]
                            step = 1
                        else:
                            start, stop, step = args_vals[0], args_vals[1], args_vals[2]
                        rng = list(range(start, stop, step))
                        if len(rng) > 20:
                            return None
                        for v in rng:
                            values.append(cst.Integer(value=str(v)))
                    except Exception:
                        return None
                else:
                    return None
            else:
                # Name reference to prior literal assignment within same function
                if isinstance(iter_node, cst.Name):
                    name_to_find = iter_node.value
                    assignments_found = None
                    # search only the statements that come before the for-loop
                    for prev in body_stmts[:first_index]:
                        if isinstance(prev, cst.SimpleStatementLine) and len(prev.body) == 1:
                            expr = prev.body[0]
                            if isinstance(expr, cst.Assign):
                                if len(expr.targets) == 1 and isinstance(expr.targets[0].target, cst.Name):
                                    tgt = expr.targets[0].target.value
                                    if tgt == name_to_find:
                                        maybe_vals = _extract_from_list_or_tuple(expr.value)
                                        if maybe_vals is not None:
                                            assignments_found = maybe_vals
                    if assignments_found:
                        values = assignments_found
                    else:
                        return None
                else:
                    return None

        param_list = cst.List([cst.Element(value=v) for v in values])
        params_str = cst.SimpleString(value=f'"{param_name}"')
        mark_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
        param_call = cst.Call(
            func=cst.Attribute(value=mark_attr, attr=cst.Name(value="parametrize")),
            args=[
                cst.Arg(value=params_str),
                cst.Arg(value=param_list),
            ],
        )
        new_decorator = cst.Decorator(decorator=param_call)

        existing_decorators = list(updated_func.decorators or [])
        for d in existing_decorators:
            try:
                if isinstance(d.decorator, cst.Call):
                    f = d.decorator.func
                    if isinstance(f, cst.Attribute) and isinstance(f.attr, cst.Name) and f.attr.value == "parametrize":
                        return None
                    if isinstance(f, cst.Name) and f.value == "parametrize":
                        return None
            except Exception:
                continue

        new_decorators = [new_decorator] + existing_decorators

        if not isinstance(first.target, cst.Name) or first.target.value != param_name:
            return None

        new_body = cst.IndentedBlock(body=list(inner_body.body))
        new_func = updated_func.with_changes(decorators=new_decorators, body=new_body)
        transformer.needs_pytest_import = True
        return new_func
    except Exception:
        return None


def convert_subtests_in_body(statements: Sequence[cst.CSTNode]) -> list[cst.BaseStatement]:
    """Convert ``with self.subTest(...)`` items to ``subtests.test(...)``.

    This helper walks the provided statement sequence and replaces
    occurrences of ``with self.subTest(...)`` (or ``with cls.subTest``)
    with a call to ``subtests.test(...)`` by rewriting the WithItem to
    call ``subtests.test`` with the same arguments. Nested blocks are
    processed recursively.

    Args:
        statements: A sequence of libcst statement nodes to transform.

    Returns:
        A list of transformed :class:`libcst.BaseStatement` nodes.
    """

    out: list[cst.BaseStatement] = []
    for stmt in statements:
        if isinstance(stmt, cst.With):
            items = stmt.items
            if len(items) == 1 and isinstance(items[0].item, cst.Call):
                call = items[0].item
                if isinstance(call.func, cst.Attribute) and isinstance(call.func.value, cst.Name):
                    if call.func.value.value in {"self", "cls"} and call.func.attr.value == "subTest":
                        new_func = cst.Attribute(value=cst.Name(value="subtests"), attr=cst.Name(value="test"))
                        new_call = cst.Call(func=new_func, args=call.args)
                        new_item = cst.WithItem(new_call)
                        new_body = stmt.body
                        if isinstance(new_body, cst.IndentedBlock):
                            converted_inner = convert_subtests_in_body(new_body.body)
                            new_body = new_body.with_changes(body=converted_inner)
                        new_with = stmt.with_changes(items=[new_item], body=new_body)
                        out.append(new_with)
                        continue

        if hasattr(stmt, "body") and isinstance(stmt.body, cst.IndentedBlock):
            inner_block = stmt.body
            converted = convert_subtests_in_body(inner_block.body)
            new_block = inner_block.with_changes(body=converted)
            try:
                new_stmt = stmt.with_changes(body=new_block)  # type: ignore[arg-type]
                out.append(new_stmt)
                continue
            except Exception:
                out.append(stmt)
                continue

        out.append(stmt)

    return out


def body_uses_subtests(statements: Sequence[cst.CSTNode]) -> bool:
    """Return True when a statement body uses the `subtests.test` helper.

    Args:
        statements: Sequence of libcst statement nodes to inspect.

    Returns:
        ``True`` if any ``with`` item calls ``subtests.test(...);``
        otherwise ``False``.
    """

    for stmt in statements:
        if isinstance(stmt, cst.With):
            for item in stmt.items:
                if isinstance(item.item, cst.Call) and isinstance(item.item.func, cst.Attribute):
                    func = item.item.func
                    if isinstance(func.value, cst.Name) and func.value.value == "subtests":
                        if func.attr.value == "test":
                            return True
    return False


def ensure_subtests_param(func: cst.FunctionDef) -> cst.FunctionDef:
    """Ensure the function has a ``subtests`` parameter.

    If ``func`` already declares a ``subtests`` parameter the original
    function is returned. Otherwise the helper appends a new parameter
    named ``subtests`` and returns an updated FunctionDef.

    Args:
        func: The :class:`libcst.FunctionDef` to update.

    Returns:
        A :class:`libcst.FunctionDef` that includes a ``subtests``
        parameter.
    """

    params = list(func.params.params)
    for p in params:
        if isinstance(p.name, cst.Name) and p.name.value == "subtests":
            return func
    new_param = cst.Param(name=cst.Name(value="subtests"))
    params.append(new_param)
    new_params = func.params.with_changes(params=params)
    return func.with_changes(params=new_params)
