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


# Local copy of inference helpers (ported from legacy generator) to avoid
# import-time cycles. Returns (Annotation node, set of typing names)
def _get_callable_name(node: Any) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        parts: list[str] = []
        cur: Any = node
        while isinstance(cur, cst.Attribute):
            if isinstance(getattr(cur, "attr", None), cst.Name):
                parts.append(cur.attr.value)
            val = getattr(cur, "value", None)
            if isinstance(val, cst.Name):
                parts.append(val.value)
                break
            cur = val
        return ".".join(reversed(parts)) if parts else None
    return None


def _infer_ann(node: Any) -> tuple[cst.Annotation, set[str]]:
    typing_needed_local: set[str] = set()
    if isinstance(node, cst.SimpleString):
        return cst.Annotation(annotation=cst.Name("str")), typing_needed_local
    if isinstance(node, cst.Integer):
        return cst.Annotation(annotation=cst.Name("int")), typing_needed_local
    if isinstance(node, cst.Float):
        return cst.Annotation(annotation=cst.Name("float")), typing_needed_local
    if isinstance(node, cst.Name) and node.value in ("True", "False"):
        return cst.Annotation(annotation=cst.Name("bool")), typing_needed_local

    if isinstance(node, cst.List):
        elems = [getattr(e, "value", None) for e in node.elements or []]
        if elems:
            inner_ann_nodes: list[cst.BaseExpression] = []
            for e in elems:
                ann_e, names_e = (
                    _infer_ann(e) if e is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
                )
                inner_ann_nodes.append(ann_e.annotation)
                typing_needed_local.update(names_e)
            try:
                inner_names = [getattr(a, "value", None) if isinstance(a, cst.Name) else None for a in inner_ann_nodes]
            except Exception:
                inner_names = [None for _ in inner_ann_nodes]
            if inner_names and all(n == inner_names[0] and n is not None for n in inner_names):
                typing_needed_local.add("List")
                return (
                    cst.Annotation(
                        annotation=cst.Subscript(
                            value=cst.Name("List"),
                            slice=[cst.SubscriptElement(slice=cst.Index(value=inner_ann_nodes[0]))],
                        )
                    ),
                    typing_needed_local,
                )
        typing_needed_local.update({"List", "Any"})
        return (
            cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("List"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ),
            typing_needed_local,
        )

    if isinstance(node, cst.Tuple):
        elems = [getattr(e, "value", None) for e in node.elements or []]
        if elems:
            ann_parts: list[cst.BaseExpression] = []
            for e in elems:
                ann, names = _infer_ann(e) if e is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
                ann_parts.append(ann.annotation)
                typing_needed_local.update(names)
            typing_needed_local.add("Tuple")
            subslices = [cst.SubscriptElement(slice=cst.Index(value=a)) for a in ann_parts]
            return cst.Annotation(
                annotation=cst.Subscript(value=cst.Name("Tuple"), slice=subslices)
            ), typing_needed_local
        typing_needed_local.update({"Tuple", "Any"})
        return (
            cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("Tuple"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ),
            typing_needed_local,
        )

    if isinstance(node, cst.Set):
        elems = [getattr(e, "value", None) for e in node.elements or []]
        if elems:
            inner_ann, names = (
                _infer_ann(elems[0]) if elems[0] is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
            )
            typing_needed_local.update(names)
            typing_needed_local.add("Set")
            return cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("Set"), slice=[cst.SubscriptElement(slice=cst.Index(value=inner_ann.annotation))]
                )
            ), typing_needed_local
        typing_needed_local.update({"Set", "Any"})
        return (
            cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("Set"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ),
            typing_needed_local,
        )

    if isinstance(node, cst.Dict):
        elems = [e for e in node.elements or [] if isinstance(e, cst.DictElement)]
        if elems:
            k = getattr(elems[0], "key", None)
            v = getattr(elems[0], "value", None)
            k_ann, k_names = _infer_ann(k) if k is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
            v_ann, v_names = _infer_ann(v) if v is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
            typing_needed_local.update(k_names)
            typing_needed_local.update(v_names)
            typing_needed_local.add("Dict")
            return (
                cst.Annotation(
                    annotation=cst.Subscript(
                        value=cst.Name("Dict"),
                        slice=[
                            cst.SubscriptElement(slice=cst.Index(value=k_ann.annotation)),
                            cst.SubscriptElement(slice=cst.Index(value=v_ann.annotation)),
                        ],
                    )
                ),
                typing_needed_local,
            )
        typing_needed_local.update({"Dict", "Any"})
        return (
            cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("Dict"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ),
            typing_needed_local,
        )

    if getattr(cst, "ListComp", None) and isinstance(node, cst.ListComp):
        typing_needed_local.update({"List", "Any"})
        return (
            cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("List"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ),
            typing_needed_local,
        )
    if getattr(cst, "GeneratorExp", None) and isinstance(node, cst.GeneratorExp):
        typing_needed_local.update({"List", "Any"})
        return (
            cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("List"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ),
            typing_needed_local,
        )

    if isinstance(node, cst.Call):
        fname = _get_callable_name(node.func)
        if fname and fname.endswith("Path"):
            return cst.Annotation(annotation=cst.Name("str")), typing_needed_local
        if fname in ("list", "tuple", "set"):
            if node.args:
                inner = getattr(node.args[0], "value", None)
                inner_ann, inner_names_set = (
                    _infer_ann(inner) if inner is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
                )
                typing_needed_local.update(inner_names_set)
                typing_needed_local.add("List")
                return (
                    cst.Annotation(
                        annotation=cst.Subscript(
                            value=cst.Name("List"),
                            slice=[cst.SubscriptElement(slice=cst.Index(value=inner_ann.annotation))],
                        )
                    ),
                    typing_needed_local,
                )
            typing_needed_local.update({"List", "Any"})
            return (
                cst.Annotation(
                    annotation=cst.Subscript(
                        value=cst.Name("List"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                    )
                ),
                typing_needed_local,
            )
        if fname == "dict":
            typing_needed_local.add("Dict")
            return cst.Annotation(annotation=cst.Name("Dict")), typing_needed_local

    typing_needed_local.add("Any")
    return cst.Annotation(annotation=cst.Name("Any")), typing_needed_local


@dataclass
class SimpleFixtureSpec:
    name: str
    value_expr: Optional[cst.BaseExpression]
    cleanup_statements: List[Any]
    yield_style: bool


def _is_dir_like(name: str) -> bool:
    return any(k in name for k in ("dir", "path", "temp"))


def generator(context: dict[str, Any]) -> dict[str, Any]:
    maybe_out = context.get("collector_output")
    out = maybe_out if isinstance(maybe_out, CollectorOutput) else None
    if out is None:
        return {}

    fixture_specs: Dict[str, SimpleFixtureSpec] = {}
    fixture_nodes: List[cst.BaseStatement] = []
    needs_typing: Set[str] = set()
    needs_shutil = False
    module_node = context.get("module")
    existing_top_names: set[str] = set()
    try:
        if module_node and isinstance(module_node, cst.Module):
            for b in getattr(module_node, "body", []) or []:
                # collect top-level functions and classes
                if isinstance(b, cst.FunctionDef):
                    existing_top_names.add(b.name.value)
                elif isinstance(b, cst.ClassDef):
                    existing_top_names.add(b.name.value)
                # collect simple top-level assignments (names)
                elif isinstance(b, cst.SimpleStatementLine):
                    for stmt in getattr(b, "body", []) or []:
                        if isinstance(stmt, cst.Assign):
                            for targ in getattr(stmt, "targets", []) or []:
                                t = getattr(targ, "target", None)
                                if isinstance(t, cst.Name):
                                    existing_top_names.add(t.value)
                                elif isinstance(t, cst.Tuple):
                                    for el in getattr(t, "elements", []) or []:
                                        v = getattr(el, "value", None)
                                        if isinstance(v, cst.Name):
                                            existing_top_names.add(v.value)
                        elif isinstance(stmt, cst.AnnAssign):
                            t = getattr(stmt, "target", None)
                            if isinstance(t, cst.Name):
                                existing_top_names.add(t.value)
                elif isinstance(b, cst.AnnAssign):
                    t = getattr(b, "target", None)
                    if isinstance(t, cst.Name):
                        existing_top_names.add(t.value)
    except Exception:
        existing_top_names = set()

    # For each collected class, decide whether to synthesize a temp_dirs
    # composite fixture and which attributes are handled there.
    for cls_name, cls in out.classes.items():
        # detect composite temp_dirs groups: if multiple dir-like attributes
        # exist and teardown references them, synthesize a composite fixture
        composite_attrs: set[str] = set()
        try:
            dir_like = [a for a in getattr(cls, "setup_assignments", {}) if _is_dir_like(a)]
            if len(dir_like) >= 2:
                # require explicit self.<attr> references in teardown to synthesize composite
                mentions = False
                for stmt in getattr(cls, "teardown_statements", []) or []:
                    try:
                        code = cst.Module(body=[stmt]).code
                        if any((f"self.{a}" in code) for a in dir_like):
                            mentions = True
                            break
                    except Exception:
                        pass
                if mentions:
                    composite_attrs.update(dir_like)
        except Exception:
            composite_attrs = set()

        # We intentionally do not synthesize a composite `temp_dirs` fixture here.
        # Per the user's preference, emit per-attribute fixtures for each
        # collected attribute. The narrower NamedTuple bundling (for multiple
        # locals coming from the same helper call) remains implemented below.
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

            # Only treat the attribute as yield-style when we find teardown
            # statements that explicitly reference the attribute (e.g. via
            # `self.<attr>`). We used to conservatively assume any dir-like
            # attribute should be yield-style when the class had teardown
            # statements, but that leads to over-eager binding (creating
            # local temporaries) for attributes like `config_dir` which are
            # merely derived from `temp_dir`. Keep the behavior strict:
            # relevant_cleanup must mention the attribute to force yield-style.

            yield_style = bool(relevant_cleanup)
            fixture_specs[attr] = SimpleFixtureSpec(
                name=attr,
                value_expr=val if isinstance(val, cst.BaseExpression) else None,
                cleanup_statements=relevant_cleanup,
                yield_style=yield_style,
            )

            # generate a trivial fixture node: either yield-style with cleanup or return-style
            decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))

            # Determine other attribute dependencies referenced as self.<name>
            def _collect_self_attrs(node: Any) -> set[str]:
                found: set[str] = set()
                if node is None or not isinstance(node, cst.BaseExpression):
                    return found
                if isinstance(node, cst.Attribute):
                    if isinstance(getattr(node, "value", None), cst.Name) and getattr(node.value, "value", None) in (
                        "self",
                        "cls",
                    ):
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
                                                func=cst.Attribute(
                                                    value=cst.Name(attr if not attr.startswith("self.") else attr),
                                                    attr=cst.Name("mkdir"),
                                                ),
                                                args=[cst.Arg(keyword=cst.Name("parents"), value=cst.Name("True"))],
                                            )
                                        )
                                    ]
                                )
                                setup_stmts.append(cast(cst.BaseStatement, mkdir_call.visit(_ReplaceSelfWithName())))

            # decide whether to bind to a local. For literal scalars, prefer
            # yielding the literal directly so teardown that assigns back to
            # the attribute remains simple (e.g. "value = None"). For non-
            # literal expressions, bind to a generated local var and rewrite
            # cleanup to reference that local.
            def _is_literal_scalar(node: Any) -> bool:
                return isinstance(node, (cst.SimpleString, cst.Integer, cst.Float)) or (
                    isinstance(node, cst.Name) and getattr(node, "value", None) in ("True", "False")
                )

            # attempt to infer filename literals from local assignments when autocreate
            try:
                autocreate = bool(context.get("autocreate", True))
            except Exception:
                autocreate = True
            try:
                if (
                    autocreate
                    and isinstance(val, cst.Call)
                    and isinstance(val.func, cst.Name)
                    and val.func.value in ("str",)
                ):
                    if val.args:
                        first = getattr(val.args[0], "value", None)
                        if isinstance(first, cst.Name):
                            local_map = getattr(cls, "local_assignments", {}) or {}
                            mapped = local_map.get(first.value)
                            if isinstance(mapped, tuple):
                                assigned_call, idx = mapped
                            else:
                                assigned_call, idx = mapped, None
                            if isinstance(assigned_call, cst.Call):
                                try:
                                    if idx is not None and 0 <= idx < len(assigned_call.args):
                                        cand = getattr(assigned_call.args[idx], "value", None)
                                        if isinstance(cand, cst.SimpleString):
                                            val = cand
                                except Exception:
                                    pass
                                for arg_item in getattr(assigned_call, "args", []) or []:
                                    if (
                                        getattr(arg_item, "keyword", None)
                                        and isinstance(arg_item.keyword, cst.Name)
                                        and arg_item.keyword.value == "filename"
                                    ):
                                        cand = getattr(arg_item, "value", None)
                                        if isinstance(cand, cst.SimpleString):
                                            val = cand
                                fname = _get_callable_name(assigned_call.func)
                                if fname and fname.endswith("Path"):
                                    for arg_item in getattr(assigned_call, "args", []) or []:
                                        cand = getattr(arg_item, "value", None)
                                        if isinstance(cand, cst.SimpleString):
                                            val = cand
            except Exception:
                pass

            if yield_style and isinstance(val, cst.BaseExpression):
                # attempt to infer filename literals from local assignments when autocreate
                try:
                    autocreate = bool(context.get("autocreate", True))
                except Exception:
                    autocreate = True
                # if val is a wrapper like str(sql_file) and autocreate is enabled,
                # inspect local_assignments to replace the wrapper with the original
                # literal (filename) when possible.
                try:
                    if (
                        autocreate
                        and isinstance(val, cst.Call)
                        and isinstance(val.func, cst.Name)
                        and val.func.value in ("str",)
                    ):
                        # expect first arg to be a Name referencing local
                        if val.args:
                            first = getattr(val.args[0], "value", None)
                            if isinstance(first, cst.Name):
                                local_map = getattr(cls, "local_assignments", {}) or {}
                                mapped = local_map.get(first.value)
                                if isinstance(mapped, tuple):
                                    assigned_call, idx = mapped
                                else:
                                    assigned_call, idx = mapped, None
                                if isinstance(assigned_call, cst.Call):
                                    # check positional index
                                    try:
                                        if idx is not None and 0 <= idx < len(assigned_call.args):
                                            cand = getattr(assigned_call.args[idx], "value", None)
                                            if isinstance(cand, cst.SimpleString):
                                                val = cand
                                    except Exception:
                                        pass
                                    # check keyword 'filename'
                                    for arg_item in getattr(assigned_call, "args", []) or []:
                                        if (
                                            getattr(arg_item, "keyword", None)
                                            and isinstance(arg_item.keyword, cst.Name)
                                            and arg_item.keyword.value == "filename"
                                        ):
                                            cand = getattr(arg_item, "value", None)
                                            if isinstance(cand, cst.SimpleString):
                                                val = cand
                                    # path constructor
                                    fname = _get_callable_name(assigned_call.func)
                                    if fname and fname.endswith("Path"):
                                        for arg_item in getattr(assigned_call, "args", []) or []:
                                            cand = getattr(arg_item, "value", None)
                                            if isinstance(cand, cst.SimpleString):
                                                val = cand
                except Exception:
                    pass

                # If cleanup references self.<attr> in anything other than a simple
                # assignment (self.attr = ...), prefer binding. If it's only a
                # simple assignment we can yield literal directly.
                # If the attribute was assigned multiple times during setUp,
                # prefer binding to a local to avoid collisions and make
                # cleanup rewriting unambiguous (e.g. self.x assigned more
                # than once). This ensures unique local names are created
                # for cases like multiple assignments in setUp.
                must_bind = False
                try:
                    if isinstance(assigns, list) and len(assigns) > 1:
                        must_bind = True
                except Exception:
                    pass
                for s in relevant_cleanup:
                    try:
                        code = cst.Module(body=[s]).code.strip()
                        if f"self.{attr}" in code:
                            # if it starts with 'self.<attr> =' it's a simple assignment
                            if not code.startswith(f"self.{attr} ="):
                                must_bind = True
                                break
                    except Exception:
                        must_bind = True
                        break
                # compute conventional local base name and avoid literal-yield
                # when module-level underscore-prefixed names exist; this
                # reduces risk of accidental name collisions for generated
                # locals (e.g., _x_value).
                base_local = f"_{attr}_value"
                try:
                    if any(n.startswith("_") for n in existing_top_names):
                        must_bind = True
                except Exception:
                    pass
                if _is_literal_scalar(val) and not must_bind:
                    # yield literal directly, preserve original cleanup statements
                    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(val))])
                    rewritten_cleanup: list[cst.BaseStatement] = list(relevant_cleanup)
                    body = cst.IndentedBlock(body=[yield_stmt] + rewritten_cleanup)
                    func = cst.FunctionDef(
                        name=cst.Name(attr), params=cst.Parameters(params=params), body=body, decorators=[decorator]
                    )
                else:
                    # Bind yield-style fixtures to a generated local variable so
                    # tearDown references can be rewritten safely. This avoids
                    # yielding literals directly which complicates cleanup.
                    # ensure unique local var name
                    base_local = f"_{attr}_value"
                    local_var = base_local
                    i = 1
                    # avoid collisions with module-level/top-level names
                    while local_var in locals() or local_var in globals() or local_var in existing_top_names:
                        local_var = f"{base_local}_{i}"
                        i += 1

                    # create assignment to local_var
                    assign = cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[cst.AssignTarget(target=cst.Name(local_var))],
                                value=cast(cst.BaseExpression, val.visit(_ReplaceSelfWithName())),
                            )
                        ]
                    )

                    # yield the local_var
                    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(cst.Name(local_var)))])

                    # rewrite cleanup to reference the local_var instead of self.attr
                    rewritten_cleanup = []
                    for s in relevant_cleanup:
                        new_s = cast(cst.BaseStatement, s.visit(_ReplaceSelfWithName()))

                        class _ReplaceAttrWithLocal(cst.CSTTransformer):
                            def leave_Name(self, original: cst.Name, updated: cst.Name) -> cst.BaseExpression:
                                if original.value == attr:
                                    return cst.Name(local_var)
                                return updated

                        new_s = cast(cst.BaseStatement, new_s.visit(_ReplaceAttrWithLocal()))
                        rewritten_cleanup.append(new_s)

                    include_setup = not bool(getattr(cls, "setup_methods", []))
                    body = cst.IndentedBlock(
                        body=([assign] if include_setup else [assign]) + [yield_stmt] + rewritten_cleanup
                    )
                    func = cst.FunctionDef(
                        name=cst.Name(attr), params=cst.Parameters(params=params), body=body, decorators=[decorator]
                    )
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
                                                    func=cst.Attribute(
                                                        value=cst.Name(attr if not attr.startswith("self.") else attr),
                                                        attr=cst.Name("mkdir"),
                                                    ),
                                                    args=[cst.Arg(keyword=cst.Name("parents"), value=cst.Name("True"))],
                                                )
                                            )
                                        ]
                                    )
                                    preserved_setup.append(
                                        cast(cst.BaseStatement, mkdir_call.visit(_ReplaceSelfWithName()))
                                    )

                include_setup = not bool(getattr(cls, "setup_methods", []))
                body = cst.IndentedBlock(body=(preserved_setup if include_setup else []) + [return_stmt])
                # try to infer a precise return annotation for this fixture
                try:
                    ann_res, names_req = _infer_ann(val)
                    needs_typing.update(names_req)
                    # Only emit a return annotation when it's more specific than Any.
                    ann_node = getattr(ann_res, "annotation", None)
                    # Emit return annotations when they are useful and stable.
                    # Allow simple Name annotations (e.g., "int", "Path") and
                    # Tuple[...] subscript annotations (commonly inferred for
                    # tuple literals). Skip other complex/subscript annotations
                    # to avoid noisy goldens.
                    if isinstance(ann_node, cst.Name):
                        if getattr(ann_node, "value", None) == "Any":
                            func = cst.FunctionDef(
                                name=cst.Name(attr),
                                params=cst.Parameters(params=params),
                                body=body,
                                decorators=[decorator],
                            )
                        else:
                            func = cst.FunctionDef(
                                name=cst.Name(attr),
                                params=cst.Parameters(params=params),
                                body=body,
                                decorators=[decorator],
                                returns=ann_res,
                            )
                    elif (
                        isinstance(ann_node, cst.Subscript)
                        and isinstance(getattr(ann_node, "value", None), cst.Name)
                        and getattr(ann_node.value, "value", None) in ("Tuple", "List")
                    ):
                        # allow Tuple[...] annotations for tuple literals
                        func = cst.FunctionDef(
                            name=cst.Name(attr),
                            params=cst.Parameters(params=params),
                            body=body,
                            decorators=[decorator],
                            returns=ann_res,
                        )
                    else:
                        func = cst.FunctionDef(
                            name=cst.Name(attr), params=cst.Parameters(params=params), body=body, decorators=[decorator]
                        )
                except Exception:
                    func = cst.FunctionDef(
                        name=cst.Name(attr), params=cst.Parameters(params=params), body=body, decorators=[decorator]
                    )
            else:
                # fallback: return None
                return_stmt = cst.SimpleStatementLine(body=[cst.Return(cst.Name("None"))])
                body = cst.IndentedBlock(body=[return_stmt])
                func = cst.FunctionDef(name=cst.Name(attr), params=cst.Parameters(), body=body, decorators=[decorator])

            fixture_nodes.append(func)

            # add typing names inferred from value expression
            try:
                if isinstance(val, cst.BaseExpression):
                    ann_res, names_req = _infer_ann(val)
                    needs_typing.update(names_req)
            except Exception:
                pass

                # minimal typing inference: if dict literal, add typing names.
                # For sequence/tuple/set literals we rely on _infer_ann above to
                # provide precise typing requirements. Avoid unconditionally
                # adding 'Any' here because it pollutes generated imports and
                # golden outputs when a precise annotation (e.g., Tuple[str,int])
                # was inferred.
            try:
                if isinstance(val, (cst.Dict,)):
                    needs_typing.update({"Dict"})
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

    # If setUp contains tuple-unpacking from a helper call (recorded in
    # local_assignments), synthesize a NamedTuple container and a bundled
    # fixture that constructs and yields it. This is narrower than the old
    # composite heuristics: we only bundle when multiple locals come from the
    # same Call and those locals map to attributes recorded in setup_assignments.
    try:
        used_names: set[str] = set()
        for cls_name, cls in out.classes.items():
            local_map = getattr(cls, "local_assignments", {}) or {}
            # group by the assigned call expression source
            call_groups: dict[str, list[tuple[str, int, Any]]] = {}
            for local_name, val in local_map.items():
                assigned_call, idx = val if isinstance(val, tuple) else (val, None)
                if not isinstance(assigned_call, cst.Call):
                    continue
                try:
                    key = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(assigned_call)])]).code
                except Exception:
                    key = repr(assigned_call)
                call_groups.setdefault(key, []).append((local_name, idx, assigned_call))

            for group in call_groups.values():
                if len(group) < 2:
                    continue
                # map locals to attributes if possible
                local_to_attr: dict[str, str] = {}
                for local_name, idx, assigned_call in group:
                    for attr_name, assigns in getattr(cls, "setup_assignments", {}).items():
                        v = assigns[-1] if isinstance(assigns, list) and assigns else assigns
                        if isinstance(v, cst.Name) and v.value == local_name:
                            local_to_attr[local_name] = attr_name
                        elif local_name == attr_name:
                            local_to_attr[local_name] = attr_name
                        elif isinstance(v, cst.Call) and v.args:
                            for arg_item in v.args:
                                a_val = getattr(arg_item, "value", None)
                                if isinstance(a_val, cst.Name) and a_val.value == local_name:
                                    local_to_attr[local_name] = attr_name
                                    break

                if not local_to_attr:
                    continue

                # derive container and fixture names from TestCase class name
                def _derive_names(class_name: str) -> tuple[str, str]:
                    base = class_name
                    if base.startswith("Test") and len(base) > 4:
                        base = base[4:]
                    if not base:
                        base = class_name
                    named = f"_{base}Data"
                    import re

                    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", base)
                    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
                    fixture_nm = f"{snake}_data"
                    return named, fixture_nm

                namedtuple_name, fixture_name = _derive_names(cls_name)
                # ensure uniqueness for namedtuple and fixture against module names
                if namedtuple_name in used_names or namedtuple_name in existing_top_names:
                    # skip if conflicting
                    continue
                used_names.add(namedtuple_name)
                # avoid fixture name colliding with existing top-level names
                if fixture_name in existing_top_names:
                    suffix_i = 1
                    base = fixture_name
                    while f"{base}_{suffix_i}" in existing_top_names:
                        suffix_i += 1
                    fixture_name = f"{base}_{suffix_i}"

                # build a minimal NamedTuple class with Any annotations
                class_body: list[cst.BaseStatement] = []
                class_body.append(
                    cst.SimpleStatementLine(
                        body=[cst.Expr(cst.SimpleString('"""Container for test data and resources."""'))]
                    )
                )
                sorted_group = sorted(group, key=lambda x: (x[1] if x[1] is not None else 0))
                for local, _, _ in sorted_group:
                    attr = local_to_attr.get(local, local)
                    ann_assign = cst.AnnAssign(
                        target=cst.Name(attr), annotation=cst.Annotation(annotation=cst.Name("Any")), value=None
                    )
                    class_body.append(cst.SimpleStatementLine(body=[ann_assign]))

                class_def = cst.ClassDef(
                    name=cst.Name(namedtuple_name),
                    bases=[cst.Arg(value=cst.Name("NamedTuple"))],
                    body=cst.IndentedBlock(body=class_body),
                )

                # emit fixture that assigns call result to locals and yields the NamedTuple
                assigned_call = group[0][2]

                # replace self.* with bare names
                class _ReplaceSelf(cst.CSTTransformer):
                    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
                        if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
                            if isinstance(original.attr, cst.Name):
                                return cst.Name(original.attr.value)
                        return updated

                call_in_fixture = assigned_call.visit(_ReplaceSelf())
                targets = [cst.Name(local) for local, _, _ in sorted_group]
                assign_target = cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Tuple(elements=[cst.Element(value=t) for t in targets]))],
                    value=call_in_fixture,
                )
                assign_stmt = cst.SimpleStatementLine(body=[assign_target])

                ctor_args = [cst.Arg(value=cst.Name(local)) for local, _, _ in sorted_group]
                ctor = cst.Call(func=cst.Name(namedtuple_name), args=ctor_args)
                yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(ctor))])
                decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
                body = cst.IndentedBlock(body=[assign_stmt, yield_stmt])
                fixture_func = cst.FunctionDef(
                    name=cst.Name(fixture_name), params=cst.Parameters(), body=body, decorators=[decorator]
                )

                # prepend class_def and fixture to fixture_nodes
                fixture_nodes.insert(0, class_def)
                fixture_nodes.insert(1, fixture_func)
                # request typing import names
                try:
                    needs_typing.update({"NamedTuple", "Any"})
                except Exception:
                    pass
    except Exception:
        pass

    result: dict[str, Any] = {"fixture_specs": fixture_specs, "fixture_nodes": fixture_nodes}
    if needs_typing:
        result["needs_typing_names"] = sorted(needs_typing)
    if needs_shutil:
        result["needs_shutil_import"] = True
    return result


# Backwards-compatibility helpers for tests that import the module and
# expect `generator_stage` and `_is_literal` at module level. These are
# lightweight aliases that map to the canonical implementation above.
def generator_stage(context: dict[str, Any]) -> dict[str, Any]:
    return generator(context)


def _is_literal(node: Any) -> bool:
    """Compatibility: checks whether a node is a literal scalar.

    Tests historically called generator._is_literal; keep a thin wrapper
    around the internal scalar check used in this module.
    """
    try:
        return isinstance(node, (cst.SimpleString, cst.Integer, cst.Float)) or (
            isinstance(node, cst.Name) and getattr(node, "value", None) in ("True", "False")
        )
    except Exception:
        return False
