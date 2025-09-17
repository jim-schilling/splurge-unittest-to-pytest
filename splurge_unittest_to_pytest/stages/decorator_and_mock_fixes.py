"""Convert unittest decorators to pytest markers and fix mock imports.

Rewrite decorators such as ``@unittest.skip`` into ``pytest.mark.skip`` and
clean problematic ``from unittest.mock import ...`` imports so converted
modules remain importable and compatible with pytest.

Publics:
    DecoratorAndMockTransformer
"""

from __future__ import annotations

from typing import Any, cast
import importlib
import json
import importlib.resources as pkg_resources

import libcst as cst

DOMAINS = ["stages", "mocks"]

# Associated domains for this module


class DecoratorAndMockTransformer(cst.CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self._module: cst.Module | None = None

    def visit_Module(self, node: cst.Module) -> None:
        # store module AST to allow context-aware decisions in later leaves
        self._module = node

    def leave_Decorator(self, original: cst.Decorator, updated: cst.Decorator) -> cst.Decorator:
        expr = updated.decorator

        # Helper to build pytest.mark.<name> call
        def _make_mark(name: str, args: list[cst.Arg] | None = None) -> cst.Call:
            mark_attr = cst.Attribute(
                value=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("mark")), attr=cst.Name(name)
            )
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
        if (
            isinstance(expr, cst.Attribute)
            and isinstance(expr.value, cst.Name)
            and expr.value.value == "unittest"
            and expr.attr.value == "expectedFailure"
        ):
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
                # Detect names that are not attributes of the real `unittest.mock`.
                # Load a curated mapping of known-bad names from package data so
                # we can maintain and extend this list without code edits.
                bad_names: set[str] = set()
                curated_bad: set[str] = set()
                # Fallback mapping retained for safety when resource loading fails
                FALLBACK_BAD = {"side_effect", "autospec", "sentinel"}
                try:
                    # Attempt to load curated mapping from package data
                    data_pkg = pkg_resources.files("splurge_unittest_to_pytest").joinpath(
                        "data/known_bad_mock_names.json"
                    )
                    if data_pkg.is_file():
                        raw = data_pkg.read_text(encoding="utf8")
                        parsed = json.loads(raw)
                        curated_bad = {k for k in parsed.keys()}
                    else:
                        curated_bad = FALLBACK_BAD
                except Exception:
                    curated_bad = FALLBACK_BAD

                try:
                    mock_module = importlib.import_module("unittest.mock")
                    for alias in names_seq:
                        if not isinstance(alias.name, cst.Name):
                            continue
                        name_val = alias.name.value
                        if name_val in curated_bad or not hasattr(mock_module, name_val):
                            bad_names.add(name_val)
                except Exception:
                    # conservative fallback: mark curated/fallback bad names
                    bad_names = {
                        alias.name.value
                        for alias in names_seq
                        if isinstance(alias.name, cst.Name) and alias.name.value in curated_bad
                    }
                # If the module already explicitly imports the mock module or has
                # other `from unittest.mock` imports, prefer to skip rewriting to
                # avoid duplicate/contradictory imports. However, when the set of
                # bad names contains elements we consider known-problematic, we
                # force the rewrite to ensure conversion produces importable code.
                FORCE_REWRITE_BAD = {"side_effect", "autospec", "sentinel"}
                if bad_names & FORCE_REWRITE_BAD:
                    # force rewrite regardless of other imports
                    pass
                else:
                    if self._module is not None:
                        for other in self._module.body:
                            if not (isinstance(other, cst.SimpleStatementLine) and other.body):
                                continue
                            other_expr = other.body[0]
                            # import unittest.mock as m  -> skip rewrite
                            if isinstance(other_expr, cst.Import):
                                for n in other_expr.names:
                                    if (
                                        isinstance(n.name, cst.Attribute)
                                        and getattr(n.name.attr, "value", None) == "mock"
                                    ):
                                        return updated
                            # from unittest.mock import *  OR any from-import elsewhere -> skip
                            if isinstance(other_expr, cst.ImportFrom):
                                other_mod = _dotted_name(getattr(other_expr, "module", None))
                                if other_mod == "unittest.mock":
                                    try:
                                        if other_expr is not stmt:
                                            return updated
                                    except Exception:
                                        return updated
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
                    safe = [
                        alias
                        for alias in names_seq
                        if isinstance(alias.name, cst.Name) and alias.name.value not in bad_names
                    ]
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
                        new_imp = cst.ImportFrom(
                            module=cst.Attribute(value=cst.Name("unittest"), attr=cst.Name("mock")), names=new_names
                        )
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
