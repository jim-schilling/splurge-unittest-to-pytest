"""Generator v2: small, testable generator core that mirrors the public
contract of the original generator stage but is easier to reason about and
unit test.

This implementation intentionally focuses on the behaviors requested in the
plan: deterministic composite selection for temp_dirs, per-attribute
fixtures for non-dir attrs, mkdtemp preservation, and returning the same
output shape as the original (fixture_specs and fixture_nodes).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, cast

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


@dataclass
class SimpleFixtureSpec:
    name: str
    value_expr: Optional[cst.BaseExpression]
    cleanup_statements: List[Any]
    yield_style: bool


def _is_dir_like(name: str) -> bool:
    return any(k in name for k in ("dir", "path", "temp"))


def generator_v2(context: dict[str, Any]) -> dict[str, Any]:
    maybe_out = context.get("collector_output")
    out = maybe_out if isinstance(maybe_out, CollectorOutput) else None
    if out is None:
        return {}

    fixture_specs: Dict[str, SimpleFixtureSpec] = {}
    fixture_nodes: List[cst.BaseStatement] = []
    needs_typing: Set[str] = set()
    needs_shutil = False

    # For each collected class, decide whether to synthesize a temp_dirs
    # composite fixture and which attributes are handled there.
    for cls_name, cls in out.classes.items():
        # Per-attribute emission: emit one fixture per collected attribute. This
        # intentionally avoids synthesizing composite fixtures like `temp_dirs`.
        for attr, assigns in getattr(cls, "setup_assignments", {}).items():
            val = assigns[-1] if isinstance(assigns, list) and assigns else assigns
            # find cleanup statements that mention this attr
            relevant_cleanup = []
            for stmt in getattr(cls, "teardown_statements", []):
                try:
                    if attr in cst.Module(body=[stmt]).code or f"self.{attr}" in cst.Module(body=[stmt]).code:
                        relevant_cleanup.append(stmt)
                        if "shutil" in cst.Module(body=[stmt]).code:
                            needs_shutil = True
                except Exception:
                    pass

            yield_style = bool(relevant_cleanup)
            fixture_specs[attr] = SimpleFixtureSpec(name=attr, value_expr=val if isinstance(val, cst.BaseExpression) else None, cleanup_statements=relevant_cleanup, yield_style=yield_style)

            # generate a trivial fixture node: either yield-style with cleanup or return-style
            decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
            # Determine other attribute dependencies referenced as self.<name>
            def _collect_self_attrs(node: Any) -> set[str]:
                found: set[str] = set()
                if node is None or not isinstance(node, cst.BaseExpression):
                    return found
                if isinstance(node, cst.Attribute):
                    if isinstance(getattr(node, "value", None), cst.Name) and getattr(node.value, "value", None) in ("self", "cls"):
                        if isinstance(node.attr, cst.Name):
                            found.add(node.attr.value)
                    # recurse into value and attr
                    found |= _collect_self_attrs(node.value)
                    return found
                if isinstance(node, cst.Call):
                    found |= _collect_self_attrs(node.func)
                    for a in getattr(node, "args", []) or []:
                        inner = getattr(a, "value", None)
                        found |= _collect_self_attrs(inner)
                    return found
                if isinstance(node, cst.Subscript):
                    found |= _collect_self_attrs(node.value)
                    for s in getattr(node, "slice", []) or []:
                        inner = getattr(s, "slice", None) or getattr(s, "value", None) or s
                        if isinstance(inner, cst.BaseExpression):
                            found |= _collect_self_attrs(inner)
                    return found
                if isinstance(node, (cst.Tuple, cst.List, cst.Set, cst.Dict)):
                    for e in getattr(node, "elements", []) or []:
                        val_e = getattr(e, "value", None)
                        if isinstance(val_e, cst.BaseExpression):
                            found |= _collect_self_attrs(val_e)
                    return found
                # Binary/Comp/Bool
                if isinstance(node, (cst.BinaryOperation, cst.Comparison, cst.BooleanOperation)):
                    if hasattr(node, "left") and isinstance(node.left, cst.BaseExpression):
                        found |= _collect_self_attrs(node.left)
                    if hasattr(node, "right") and isinstance(node.right, cst.BaseExpression):
                        found |= _collect_self_attrs(node.right)
                    for comp in getattr(node, "comparisons", []) or []:
                        inner = getattr(comp, "comparison", None) or getattr(comp, "operator", None)
                        if isinstance(inner, cst.BaseExpression):
                            found |= _collect_self_attrs(inner)
                    return found
                # Names and others: nothing
                return found

            other_deps = []
            if isinstance(val, cst.BaseExpression):
                deps = _collect_self_attrs(val)
                for name in sorted(deps):
                    if name != attr:
                        other_deps.append(name)

            # build params for dependencies
            params: list[cst.Param] = []
            for d in other_deps:
                params.append(cst.Param(name=cst.Name(d)))

            # transformer to replace self.X with bare X (dependency param) or local name
            class _ReplaceSelfWithName(cst.CSTTransformer):
                def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
                    if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
                        if isinstance(original.attr, cst.Name):
                            name = original.attr.value
                            return cst.Name(name)
                    return updated

            # collect mkdir/setup statements from recorded setup_methods for this attr
            setup_stmts: list[cst.BaseStatement] = []
            for m in getattr(cls, "setup_methods", []) or []:
                if isinstance(getattr(m, "body", None), cst.IndentedBlock):
                    for s in getattr(m, "body").body:
                        try:
                            code = cst.Module(body=[s]).code
                        except Exception:
                            code = ""
                        # if the parsed statement mentions mkdir for this attr,
                        # try to transform and preserve it; otherwise synthesize
                        # a canonical mkdir call only if we detected the pattern
                        if f"{attr}.mkdir(" in code or f"self.{attr}.mkdir(" in code:
                            try:
                                node = s.visit(_ReplaceSelfWithName())
                                setup_stmts.append(cast(cst.BaseStatement, node))
                                continue
                            except Exception:
                                # fallback to a synthesized mkdir(parents=True)
                                mkdir_call = cst.SimpleStatementLine(
                                    body=[
                                        cst.Expr(
                                            cst.Call(
                                                func=cst.Attribute(value=cst.Name(attr if not attr.startswith("self.") else attr), attr=cst.Name("mkdir")),
                                                args=[cst.Arg(keyword=cst.Name("parents"), value=cst.Name("True"))],
                                            )
                                        )
                                    ]
                                )
                                setup_stmts.append(cast(cst.BaseStatement, mkdir_call.visit(_ReplaceSelfWithName())))

            if yield_style and isinstance(val, cst.BaseExpression):
                # If the setup value is a simple literal, yield it directly and
                # keep cleanup statements referring to the bare attribute name
                # (e.g., value = None). For non-literals we bind to a local
                # variable and rewrite cleanup to use that local name.
                is_literal = isinstance(val, (cst.Integer, cst.Float, cst.SimpleString)) or (
                    isinstance(val, cst.Name) and getattr(val, "value", None) in ("True", "False")
                )

                # prepare a container for rewritten cleanup in either case
                rewritten_cleanup: list[cst.BaseStatement] = []

                if is_literal:
                    # yield the literal expression directly
                    yield_expr = cast(cst.BaseExpression, val.visit(_ReplaceSelfWithName()))
                    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(yield_expr))])

                    # collect setup mkdir statements (same as before)
                    setup_stmts = []
                    for m in getattr(cls, "setup_methods", []) or []:
                        if isinstance(getattr(m, "body", None), cst.IndentedBlock):
                            for s in getattr(m, "body").body:
                                try:
                                    code = cst.Module(body=[s]).code
                                except Exception:
                                    code = ""
                                if f"{attr}.mkdir(" in code or f"self.{attr}.mkdir(" in code:
                                    mkdir_call = cst.SimpleStatementLine(
                                        body=[
                                            cst.Expr(
                                                cst.Call(
                                                    func=cst.Attribute(value=cst.Name(attr if not attr.startswith("self.") else attr), attr=cst.Name("mkdir")),
                                                    args=[cst.Arg(keyword=cst.Name("parents"), value=cst.Name("True"))],
                                                )
                                            )
                                        ]
                                    )
                                    setup_stmts.append(cast(cst.BaseStatement, mkdir_call.visit(_ReplaceSelfWithName())))

                    # cleanup: only replace self.X -> X, keep bare name so it reads
                    # 'value = None' rather than binding to a generated local.
                    for s in relevant_cleanup:
                        new_s = cast(cst.BaseStatement, s.visit(_ReplaceSelfWithName()))
                        rewritten_cleanup.append(new_s)

                    # only include setup statements in the fixture body if the
                    # original class did not have setUp methods. When the
                    # class setUp remains, duplicating mkdir calls into
                    # fixtures causes duplicated behavior (see sample-04).
                    include_setup = not bool(getattr(cls, "setup_methods", []))
                    body = cst.IndentedBlock(body=(setup_stmts if include_setup else []) + [yield_stmt] + rewritten_cleanup)
                    func = cst.FunctionDef(name=cst.Name(attr), params=cst.Parameters(params=params), body=body, decorators=[decorator])
                else:
                    # non-literal: bind to a local variable and rewrite cleanup to
                    # refer to that local name so teardown runs against the
                    # yielded value variable.
                    local_var = f"_{attr}_value"
                    assign = cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[cst.AssignTarget(target=cst.Name(local_var))],
                                value=cast(cst.BaseExpression, val.visit(_ReplaceSelfWithName())),
                            )
                        ]
                    )
                    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(cst.Name(local_var)))])

                    # collect mkdir/setup statements from recorded setup_methods
                    setup_stmts = []
                    for m in getattr(cls, "setup_methods", []) or []:
                        if isinstance(getattr(m, "body", None), cst.IndentedBlock):
                            for s in getattr(m, "body").body:
                                try:
                                    code = cst.Module(body=[s]).code
                                except Exception:
                                    code = ""
                                if f"{attr}.mkdir(" in code or f"self.{attr}.mkdir(" in code:
                                    # synthesize a canonical mkdir(parents=True) call
                                    mkdir_call = cst.SimpleStatementLine(
                                        body=[
                                            cst.Expr(
                                                cst.Call(
                                                    func=cst.Attribute(value=cst.Name(attr if not attr.startswith("self.") else attr), attr=cst.Name("mkdir")),
                                                    args=[cst.Arg(keyword=cst.Name("parents"), value=cst.Name("True"))],
                                                )
                                            )
                                        ]
                                    )
                                    # replace self.X occurrences using transformer
                                    setup_stmts.append(cast(cst.BaseStatement, mkdir_call.visit(_ReplaceSelfWithName())))

                    # rewrite cleanup statements to refer to local_var or deps
                    # (rewritten_cleanup already declared above)
                    for s in relevant_cleanup:
                        new_s = cast(cst.BaseStatement, s.visit(_ReplaceSelfWithName()))
                        # additionally replace references to the attribute itself with the local_var
                        class _ReplaceAttrWithLocal(cst.CSTTransformer):
                            def leave_Name(self, original: cst.Name, updated: cst.Name) -> cst.BaseExpression:
                                if original.value == attr:
                                    return cst.Name(local_var)
                                return updated

                        new_s = cast(cst.BaseStatement, new_s.visit(_ReplaceAttrWithLocal()))
                        rewritten_cleanup.append(new_s)

                    include_setup = not bool(getattr(cls, "setup_methods", []))
                    body = cst.IndentedBlock(body=(setup_stmts if include_setup else []) + [assign, yield_stmt] + rewritten_cleanup)
                    func = cst.FunctionDef(name=cst.Name(attr), params=cst.Parameters(params=params), body=body, decorators=[decorator])
            elif not yield_style and isinstance(val, cst.BaseExpression):
                # rewrite self.* references in the return expression to params
                val_simple = cast(cst.BaseExpression, val.visit(_ReplaceSelfWithName()))
                return_stmt = cst.SimpleStatementLine(body=[cst.Return(val_simple)])

                # ensure mkdir/setup statements are preserved even for return-style
                # fixtures: detect mkdir calls in recorded setup_methods and
                # append transformed or synthesized mkdir statements.
                preserved_setup: list[cst.BaseStatement] = list(setup_stmts)
                for m in getattr(cls, "setup_methods", []) or []:
                    if isinstance(getattr(m, "body", None), cst.IndentedBlock):
                        for s in getattr(m, "body").body:
                            try:
                                code = cst.Module(body=[s]).code
                            except Exception:
                                code = ""
                            if f"{attr}.mkdir(" in code or f"self.{attr}.mkdir(" in code:
                                try:
                                    node = s.visit(_ReplaceSelfWithName())
                                    preserved_setup.append(cast(cst.BaseStatement, node))
                                except Exception:
                                    mkdir_call = cst.SimpleStatementLine(
                                        body=[
                                            cst.Expr(
                                                cst.Call(
                                                    func=cst.Attribute(value=cst.Name(attr if not attr.startswith("self.") else attr), attr=cst.Name("mkdir")),
                                                    args=[cst.Arg(keyword=cst.Name("parents"), value=cst.Name("True"))],
                                                )
                                            )
                                        ]
                                    )
                                    preserved_setup.append(cast(cst.BaseStatement, mkdir_call.visit(_ReplaceSelfWithName())))

                include_setup = not bool(getattr(cls, "setup_methods", []))
                body = cst.IndentedBlock(body=(preserved_setup if include_setup else []) + [return_stmt])
                func = cst.FunctionDef(name=cst.Name(attr), params=cst.Parameters(params=params), body=body, decorators=[decorator])
            else:
                # fallback: return None
                return_stmt = cst.SimpleStatementLine(body=[cst.Return(cst.Name("None"))])
                body = cst.IndentedBlock(body=[return_stmt])
                func = cst.FunctionDef(name=cst.Name(attr), params=cst.Parameters(), body=body, decorators=[decorator])

            fixture_nodes.append(func)

            # minimal typing inference: if dict/list literal, add typing names
            try:
                if isinstance(val, (cst.Dict,)):
                    needs_typing.update({"Dict", "Any"})
                elif isinstance(val, (cst.List, cst.Tuple, cst.Set)):
                    needs_typing.add("Any")
                # detect Path(...) usage in expressions
                if isinstance(val, cst.Call):
                    fname = None
                    if isinstance(val.func, cst.Name):
                        fname = val.func.value
                    elif isinstance(val.func, cst.Attribute):
                        fname = getattr(val.func.attr, "value", None)
                    if fname == "Path" or (isinstance(fname, str) and fname.endswith("Path")):
                        needs_typing.add("Path")
            except Exception:
                pass

    # If any fixture was yield-style, we need Generator imported
    try:
        if any(s.yield_style for s in fixture_specs.values()):
            needs_typing.add("Generator")
    except Exception:
        pass

    result: dict[str, Any] = {"fixture_specs": fixture_specs, "fixture_nodes": fixture_nodes}
    if needs_typing:
        result["needs_typing_names"] = sorted(needs_typing)
    if needs_shutil:
        result["needs_shutil_import"] = True
    return result
