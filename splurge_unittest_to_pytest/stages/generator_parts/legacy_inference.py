"""Legacy inference helpers extracted from stages/generator.py.

This module contains the previously-local helpers that infer return
annotation shapes from libcst expression nodes. It is intended as a
drop-in move to enable incremental decomposition.
"""

from __future__ import annotations

from typing import Any, Optional, Set

import libcst as cst

DOMAINS = ["generator"]

# Associated domains for this module


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


def _infer_ann(node: Any) -> tuple[cst.Annotation, Set[str]]:
    typing_needed_local: Set[str] = set()
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
