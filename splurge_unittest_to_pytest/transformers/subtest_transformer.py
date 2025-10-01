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

from .parametrize_helper import convert_subtest_loop_to_parametrize


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
    """Delegate to the parametrization helper module."""

    current = updated_func
    changed = False

    while True:
        converted = convert_subtest_loop_to_parametrize(current, current, transformer)
        if converted is None:
            break
        changed = True
        current = converted

    if not changed:
        return None

    return current


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

        # Handle statements that have an indented body (If, For, While, Try,
        # FunctionDef, ClassDef, etc.) by converting their inner blocks.
        if hasattr(stmt, "body") and isinstance(stmt.body, cst.IndentedBlock):
            inner_block = stmt.body
            converted = convert_subtests_in_body(inner_block.body)
            new_block = inner_block.with_changes(body=converted)
            try:
                # For simple cases this will return a new statement with the
                # updated body (works for If, For, While, Try, with the
                # exception of Try handlers which we handle below).
                new_stmt = stmt.with_changes(body=new_block)  # type: ignore[arg-type]
            except Exception:
                new_stmt = stmt

            # Special-case Try: we must also convert handler bodies,
            # orelse, and finalbody which are not reachable via simple
            # `with_changes(body=...)` above.
            if isinstance(stmt, cst.Try):
                # convert handlers
                new_handlers: list[cst.ExceptHandler] = []
                for h in getattr(stmt, "handlers", []) or []:
                    h_body = getattr(h, "body", None)
                    if isinstance(h_body, cst.IndentedBlock):
                        converted_h = convert_subtests_in_body(h_body.body)
                        new_h = h.with_changes(body=h_body.with_changes(body=converted_h))
                    else:
                        new_h = h
                    new_handlers.append(new_h)

                # convert orelse and finalbody
                orelse_block = getattr(stmt, "orelse", None)
                final_block = getattr(stmt, "finalbody", None)
                if isinstance(orelse_block, cst.BaseSuite):
                    converted_orelse = convert_subtests_in_body(getattr(orelse_block, "body", []))
                    new_orelse = orelse_block.with_changes(body=converted_orelse)
                else:
                    new_orelse = orelse_block

                if isinstance(final_block, cst.BaseSuite):
                    converted_final = convert_subtests_in_body(getattr(final_block, "body", []))
                    new_final = final_block.with_changes(body=converted_final)
                else:
                    new_final = final_block

                try:
                    new_try = stmt.with_changes(
                        body=new_block, handlers=new_handlers, orelse=new_orelse, finalbody=new_final
                    )
                    out.append(new_try)
                    continue
                except Exception:
                    out.append(new_stmt)
                    continue

            out.append(new_stmt)
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

    def _walk(stmts: Sequence[cst.CSTNode]) -> bool:
        for s in stmts:
            # Direct With nodes
            if isinstance(s, cst.With):
                for item in s.items:
                    if isinstance(item.item, cst.Call) and isinstance(item.item.func, cst.Attribute):
                        func = item.item.func
                        if isinstance(func.value, cst.Name) and func.value.value == "subtests":
                            if func.attr.value == "test":
                                return True
                # check nested body
                body = getattr(s.body, "body", [])
                if _walk(body):
                    return True

            # If statements: check body and orelse
            if isinstance(s, cst.If):
                if _walk(getattr(s.body, "body", [])):
                    return True
                # orelse can be an IndentedBlock, SimpleStatementSuite, or another If (elif)
                orelse = getattr(s, "orelse", None)
                if orelse:
                    # orelse may be a list of nodes in SimpleStatementSuite or an IndentedBlock
                    if isinstance(orelse, cst.BaseSuite):
                        if _walk(getattr(orelse, "body", [])):
                            return True

            # For/While loops: check body and orelse
            if isinstance(s, cst.For | cst.While):
                if _walk(getattr(s.body, "body", [])):
                    return True
                orelse = getattr(s, "orelse", None)
                if orelse and isinstance(orelse, cst.BaseSuite):
                    if _walk(getattr(orelse, "body", [])):
                        return True

            # Try: check body, handlers, orelse, finalbody
            if isinstance(s, cst.Try):
                if _walk(getattr(s.body, "body", [])):
                    return True
                for h in getattr(s, "handlers", []) or []:
                    if _walk(getattr(h.body, "body", [])):
                        return True
                if _walk(getattr(s.orelse, "body", []) if getattr(s, "orelse", None) else []):
                    return True
                if _walk(getattr(s.finalbody, "body", []) if getattr(s, "finalbody", None) else []):
                    return True

            # SimpleStatementLine may contain nested statements (rare) - inspect inner statements
            if isinstance(s, cst.SimpleStatementLine):
                for inner in getattr(s, "body", []) or []:
                    # some inner nodes might be With/If/etc.
                    if _walk([inner]):
                        return True

        return False

    return _walk(statements)


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
