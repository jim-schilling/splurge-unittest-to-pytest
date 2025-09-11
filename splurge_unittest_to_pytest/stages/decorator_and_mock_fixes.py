"""Pipeline stage to convert unittest decorators to pytest markers and
fix problematic `from unittest.mock import ...` imports introduced by conversion.

This stage is conservative and focused on the common patterns seen in the
sample data: `@unittest.skip`, `@unittest.expectedFailure`, and import lists
that include non-importable names like `side_effect`.
"""
from __future__ import annotations

from typing import Any, cast
import importlib

import libcst as cst


class DecoratorAndMockTransformer(cst.CSTTransformer):
    def leave_Decorator(self, original: cst.Decorator, updated: cst.Decorator) -> cst.Decorator:
        expr = updated.decorator
        # Helper to build pytest.mark.<name> call
        def _make_mark(name: str, args: list[cst.Arg] | None = None) -> cst.Call:
            mark_attr = cst.Attribute(value=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("mark")), attr=cst.Name(name))
            return cst.Call(func=mark_attr, args=args or [])

        # Case: Call-style decorators like @unittest.skip(...), @unittest.skipIf(...), @unittest.skipUnless(...)
        if isinstance(expr, cst.Call):
            func = expr.func
            name: str | None = None
            if isinstance(func, cst.Attribute) and isinstance(func.value, cst.Name) and func.value.value == "unittest":
                name = func.attr.value
            elif isinstance(func, cst.Name):
                name = func.value

            if name in ("skip", "skipIf", "skipUnless"):
                # helper to extract positional args and named reason
                cond = None
                reason = None
                if expr.args:
                    if len(expr.args) >= 1:
                        cond = expr.args[0].value
                    if len(expr.args) >= 2:
                        reason = expr.args[1].value
                # also check for keyword reason
                for a in expr.args:
                    if a.keyword and isinstance(a.keyword, cst.Name) and a.keyword.value == "reason":
                        reason = a.value

                if name == "skip":
                    args = []
                    if reason is not None:
                        args.append(cst.Arg(keyword=cst.Name("reason"), value=reason))
                    return updated.with_changes(decorator=_make_mark("skip", args))

                if name == "skipIf" and cond is not None:
                    args = [cst.Arg(value=cond)]
                    if reason is not None:
                        args.append(cst.Arg(keyword=cst.Name("reason"), value=reason))
                    return updated.with_changes(decorator=_make_mark("skipif", args))

                if name == "skipUnless" and cond is not None:
                    # map skipUnless(cond, reason) -> pytest.mark.skipif(not cond, reason=...)
                    not_cond = cst.UnaryOperation(operator=cst.Not(), expression=cond)
                    args = [cst.Arg(value=not_cond)]
                    if reason is not None:
                        args.append(cst.Arg(keyword=cst.Name("reason"), value=reason))
                    return updated.with_changes(decorator=_make_mark("skipif", args))
        # Case: @unittest.expectedFailure (attribute, no call) or bare expectedFailure/name
        if isinstance(expr, cst.Attribute) and isinstance(expr.value, cst.Name) and expr.value.value == "unittest" and expr.attr.value == "expectedFailure":
            return updated.with_changes(decorator=_make_mark("xfail", []))
        if isinstance(expr, cst.Name) and expr.value == "expectedFailure":
            return updated.with_changes(decorator=_make_mark("xfail", []))

        return updated

    def leave_SimpleStatementLine(self, original: cst.SimpleStatementLine, updated: cst.SimpleStatementLine) -> Any:
        # Replace an entire top-level import line when it is
        # `from unittest.mock import ...` and contains problematic names.
        try:
            if len(updated.body) != 1:
                return updated
            stmt = updated.body[0]
            if not isinstance(stmt, cst.ImportFrom):
                return updated

            imp: cst.ImportFrom = stmt

            def _dotted_name(node: cst.BaseExpression | None) -> str | None:
                if node is None:
                    return None
                if isinstance(node, cst.Name):
                    return node.value
                if isinstance(node, cst.Attribute):
                    parts = []
                    cur: cst.BaseExpression | None = node
                    while isinstance(cur, cst.Attribute):
                        parts.append(cur.attr.value)
                        cur = cur.value
                    if isinstance(cur, cst.Name):
                        parts.append(cur.value)
                        return ".".join(reversed(parts))
                return None

            module_name = _dotted_name(getattr(imp, "module", None))
            if module_name == "unittest.mock":
                # imp.names may be an ImportStar or a sequence of ImportAlias
                names_seq: list[cst.ImportAlias] = []
                if imp.names is None:
                    names_seq = []
                elif isinstance(imp.names, cst.ImportStar):
                    names_seq = []
                else:
                    # mypy: imp.names is a Sequence[ImportAlias]
                    names_seq = [n for n in imp.names if isinstance(n, cst.ImportAlias)]
                # Detect names that are not attributes of the real `unittest.mock`
                bad_names: set[str] = set()
                try:
                    mock_module = importlib.import_module("unittest.mock")
                    for alias in names_seq:
                        if not isinstance(alias.name, cst.Name):
                            continue
                        name_val = alias.name.value
                        if not hasattr(mock_module, name_val):
                            bad_names.add(name_val)
                except Exception:
                    # If we can't import the module at runtime, fall back to
                    # the conservative rule for `side_effect` only.
                    bad_names = {alias.name.value for alias in names_seq if isinstance(alias.name, cst.Name) and alias.name.value == "side_effect"}
                if bad_names:
                    # build import unittest.mock as mock
                    import_mock = cst.SimpleStatementLine(
                        body=[
                            cst.Import(
                                names=[
                                    cst.ImportAlias(
                                        name=cst.Attribute(value=cst.Name("unittest"), attr=cst.Name("mock")),
                                        asname=cst.AsName(name=cst.Name("mock")),
                                    )
                                ]
                            )
                        ]
                    )
                    safe = [alias for alias in names_seq if isinstance(alias.name, cst.Name) and alias.name.value not in bad_names]
                    nodes: list[cst.SimpleStatementLine] = [import_mock]
                    if safe:
                        # rebuild ImportFrom explicitly to avoid preserving stray
                        # punctuation/formatting from the original node
                        new_names: list[cst.ImportAlias] = []
                        for alias in safe:
                            # alias.name is a cst.Name (filtered above)
                            name_node = cst.Name(cast(str, alias.name.value))
                            asname = alias.asname if getattr(alias, "asname", None) is not None else None
                            new_names.append(cst.ImportAlias(name=name_node, asname=asname))
                        new_imp = cst.ImportFrom(module=cst.Attribute(value=cst.Name("unittest"), attr=cst.Name("mock")), names=new_names)
                        nodes.append(cst.SimpleStatementLine(body=[new_imp]))
                    return cst.FlattenSentinel(nodes)
        except Exception:
            pass
        return updated


def decorator_and_mock_fixes_stage(context: dict[str, Any]) -> dict[str, Any]:
    module = context.get("module")
    if not isinstance(module, cst.Module):
        return context
    transformer = DecoratorAndMockTransformer()
    try:
        new_module = module.visit(transformer)
        return {"module": new_module}
    except Exception:
        return context
