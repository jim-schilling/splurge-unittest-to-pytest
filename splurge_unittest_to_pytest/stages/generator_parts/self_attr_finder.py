from typing import Any, Set

import libcst as cst

DOMAINS = ["generator"]


# Associated domains for this module


def collect_self_attrs(expr: Any) -> Set[str]:
    """Collect attribute names referenced as ``self.xxx`` or ``cls.xxx``.

    Walk the given expression and return a set of referenced attribute names.
    """
    found: set[str] = set()

    def _walk(e: Any) -> None:
        if e is None:
            return
        inner = getattr(e, "target", e)
        if isinstance(inner, cst.Attribute):
            if isinstance(inner.value, cst.Name) and inner.value.value in ("self", "cls"):
                if isinstance(inner.attr, cst.Name):
                    found.add(inner.attr.value)
            _walk(inner.value)
            _walk(inner.attr)
            return
        if isinstance(inner, cst.Name):
            return
        if isinstance(inner, cst.Call):
            _walk(inner.func)
            for a in getattr(inner, "args", []) or []:
                _walk(getattr(a, "value", None))
            return
        if isinstance(inner, cst.Subscript):
            _walk(inner.value)
            for s in getattr(inner, "slice", []) or []:
                _walk(getattr(s, "slice", None) or getattr(s, "value", None) or s)
            return
        if isinstance(inner, (cst.Tuple, cst.List, cst.Set)):
            for el in getattr(inner, "elements", []) or []:
                _walk(getattr(el, "value", None) or el)
            return
        if isinstance(inner, cst.Dict):
            for el in getattr(inner, "elements", []) or []:
                _walk(getattr(el, "key", None))
                _walk(getattr(el, "value", None))
            return
        if isinstance(inner, (cst.BinaryOperation, cst.Comparison, cst.BooleanOperation)):
            if hasattr(inner, "left"):
                _walk(inner.left)
            if hasattr(inner, "right"):
                _walk(inner.right)
            for comp in getattr(inner, "comparisons", []) or []:
                _walk(getattr(comp, "comparison", None) or getattr(comp, "operator", None))
            return

    try:
        _walk(expr)
    except Exception:
        pass
    return found
