from __future__ import annotations

from typing import Tuple, Set

import libcst as cst


def type_name_for_literal(node: cst.BaseExpression) -> Tuple[cst.BaseExpression | None, Set[str]]:
    """Return an annotation node for a literal-ish expression and a set of typing names.

    Mirrors the behavior previously embedded in stages/generator.py. This
    helper focuses on common container types (List, Tuple, Set, Dict) and
    returns None when no specific typing can be inferred.
    """
    names: Set[str] = set()
    if isinstance(node, cst.List):
        names.add("List")
        elts = [getattr(e, "value", None) for e in node.elements]
        if not elts:
            inner = cst.Name("Any")
            names.add("Any")
        else:
            first = elts[0]
            if all(isinstance(e, cst.SimpleString) for e in elts if e is not None):
                inner = cst.Name("str")
            elif all(isinstance(e, cst.Integer) for e in elts if e is not None):
                inner = cst.Name("int")
            else:
                inner = cst.Name("Any")
                names.add("Any")
        sub = cst.Subscript(value=cst.Name("List"), slice=[cst.SubscriptElement(slice=cst.Index(inner))])
        return sub, names
    if isinstance(node, cst.Tuple):
        names.add("Tuple")
        parts: list[cst.BaseExpression] = []
        for el in node.elements:
            val = getattr(el, "value", None)
            if isinstance(val, cst.SimpleString):
                parts.append(cst.Name("str"))
            elif isinstance(val, cst.Integer):
                parts.append(cst.Name("int"))
            elif isinstance(val, cst.Float):
                parts.append(cst.Name("float"))
            else:
                parts.append(cst.Name("Any"))
                names.add("Any")
        subslices = [cst.SubscriptElement(slice=cst.Index(p)) for p in parts]
        sub = cst.Subscript(value=cst.Name("Tuple"), slice=subslices)
        return sub, names
    if isinstance(node, cst.Set):
        names.add("Set")
        elts = [getattr(e, "value", None) for e in node.elements]
        if elts and all(isinstance(e, cst.Integer) for e in elts if e is not None):
            inner = cst.Name("int")
        else:
            inner = cst.Name("Any")
            names.add("Any")
        sub = cst.Subscript(value=cst.Name("Set"), slice=[cst.SubscriptElement(slice=cst.Index(inner))])
        return sub, names
    if isinstance(node, cst.Dict):
        names.add("Dict")
        if node.elements:
            first = node.elements[0]
            k = getattr(first, "key", None)
            v = getattr(first, "value", None)
            if isinstance(k, cst.SimpleString):
                ktype = cst.Name("str")
            else:
                ktype = cst.Name("Any")
                names.add("Any")
            if isinstance(v, cst.Integer):
                vtype = cst.Name("int")
            else:
                vtype = cst.Name("Any")
                names.add("Any")
        else:
            ktype = cst.Name("Any")
            vtype = cst.Name("Any")
            names.add("Any")
        subslices = [cst.SubscriptElement(slice=cst.Index(ktype)), cst.SubscriptElement(slice=cst.Index(vtype))]
        sub = cst.Subscript(value=cst.Name("Dict"), slice=subslices)
        return sub, names
    return None, set()


class AnnotationInferer:
    """Simple annotation inferer used during scaffolding.

    Real implementation will inspect libcst nodes; scaffold exposes a
    predictable interface for unit testing.
    """

    def infer_return_annotation(self, func_name: str) -> str:
        # Trivial heuristic: tests can assert this behavior.
        return "-> Any" if func_name.startswith("test_") else "-> None"
