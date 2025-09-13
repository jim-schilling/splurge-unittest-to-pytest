"""FixtureGenerator stage: produce FixtureSpec entries and cst.FunctionDef fixture nodes
from CollectorOutput.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Set, cast, Sequence

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput
from splurge_unittest_to_pytest.converter.fixtures import (
    create_autocreated_file_fixture,
    create_simple_fixture_with_guard,
)


@dataclass
class FixtureSpec:
    name: str
    # value_expr can legitimately be None when collector recorded no value
    value_expr: Optional[cst.BaseExpression]
    cleanup_statements: list[Any]
    yield_style: bool
    local_value_name: Optional[str] = None


def _is_literal(expr: Optional[cst.BaseExpression]) -> bool:
    if expr is None:
        return False
    return isinstance(expr, (cst.Integer, cst.Float, cst.SimpleString, cst.Name))


def generator_stage(context: dict[str, Any]) -> dict[str, Any]:
    maybe_out: Any = context.get("collector_output")
    out: Optional[CollectorOutput] = maybe_out if isinstance(maybe_out, CollectorOutput) else None
    if out is None:
        return {}
    specs: dict[str, FixtureSpec] = {}
    # fixtures and helper AST nodes we emit; widen to BaseStatement to allow
    # imports, class defs, and function defs to be appended.
    fixture_nodes: list[cst.BaseStatement] = []
    # accumulate typing names required by generated annotations; import
    # insertion is handled by the import_injector stage based on this set.
    all_typing_needed: set[str] = set()
    used_local_names: Set[str] = set()
    # populate used_local_names from module-level identifiers to avoid collisions
    maybe_module: Any = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is not None:
        for node in module.body:
            # assignments
            if isinstance(node, cst.SimpleStatementLine):
                for stmt in node.body:
                    if isinstance(stmt, cst.Assign):
                        for t in stmt.targets:
                            target = t.target
                            if isinstance(target, cst.Name):
                                used_local_names.add(target.value)
            # def/class names
            if isinstance(node, cst.FunctionDef):
                used_local_names.add(node.name.value)
            if isinstance(node, cst.ClassDef):
                used_local_names.add(node.name.value)
            # imports - be defensive about ImportStar and name kinds
            if isinstance(node, cst.SimpleStatementLine):
                for stmt in node.body:
                    if isinstance(stmt, cst.Import):
                        for alias in getattr(stmt, "names") or []:
                            asname = getattr(alias, "asname", None)
                            if asname and isinstance(asname.name, cst.Name):
                                used_local_names.add(asname.name.value)
                            else:
                                base = None
                                nname = getattr(alias, "name", None)
                                if isinstance(nname, str):
                                    base = nname.split(".")[0]
                                else:
                                    val = getattr(nname, "value", None)
                                    if isinstance(val, str):
                                        base = val.split(".")[0]
                                if base:
                                    used_local_names.add(base)
                    if isinstance(stmt, cst.ImportFrom):
                        names = getattr(stmt, "names", None)
                        # names may be an ImportStar (not iterable) or a sequence
                        if names and isinstance(names, (list, tuple)):
                            for alias in names:
                                asname = getattr(alias, "asname", None)
                                if asname and isinstance(asname.name, cst.Name):
                                    used_local_names.add(asname.name.value)
                                else:
                                    nname = getattr(alias, "name", None)
                                    base = None
                                    if isinstance(nname, str):
                                        base = nname
                                    else:
                                        val = getattr(nname, "value", None)
                                        if isinstance(val, str):
                                            base = val
                                    if base:
                                        used_local_names.add(base)

    def _references_attribute(expr: Any, attr_name: str) -> bool:
        """Recursively check if expression references self.<attr> or bare <attr>.

        This mirrors the legacy converter's conservative search used to decide
        whether a teardown statement references a given setup attribute.
        """
        # Accept AssignTarget and similar wrapper objects by unwrapping
        expr = getattr(expr, "target", expr)
        if expr is None or not isinstance(expr, cst.BaseExpression):
            return False
        # Attribute like self.attr or cls.attr
        if isinstance(expr, cst.Attribute):
            if isinstance(expr.attr, cst.Name) and expr.attr.value == attr_name:
                if isinstance(expr.value, cst.Name) and expr.value.value in ("self", "cls"):
                    return True
            # recurse into value
            return _references_attribute(expr.value, attr_name)
        # Name
        if isinstance(expr, cst.Name):
            return expr.value == attr_name
        # Call: check func and args
        if isinstance(expr, cst.Call):
            if _references_attribute(expr.func, attr_name):
                return True
            for a in expr.args:
                if _references_attribute(a.value, attr_name):
                    return True
            return False
        # Subscript (value and slices)
        if isinstance(expr, cst.Subscript):
            if _references_attribute(expr.value, attr_name):
                return True
            for s in expr.slice:
                inner = getattr(s, "slice", None) or getattr(s, "value", None) or s
                if isinstance(inner, cst.BaseExpression) and _references_attribute(inner, attr_name):
                    return True
            return False
        # Binary/Comparison/Boolean ops
        if isinstance(expr, (cst.BinaryOperation, cst.Comparison, cst.BooleanOperation)):
            parts: list[cst.BaseExpression] = []
            if hasattr(expr, "left"):
                parts.append(expr.left)
            if hasattr(expr, "right"):
                parts.append(expr.right)
            if hasattr(expr, "comparisons"):
                for comp in expr.comparisons:
                    comp_item = getattr(comp, "comparison", None) or getattr(comp, "operator", None)
                    if comp_item is not None and isinstance(comp_item, cst.BaseExpression):
                        parts.append(comp_item)
            for p in parts:
                if _references_attribute(p, attr_name):
                    return True
            return False
        # Tuples/Lists/Sets
        if isinstance(expr, (cst.Tuple, cst.List, cst.Set)):
            for e in expr.elements:
                val = getattr(e, "value", e)
                if isinstance(val, cst.BaseExpression) and _references_attribute(val, attr_name):
                    return True
            return False
        # default: no reference found
        return False

    # snapshot module-level names to detect collisions that should force
    # binding to a local name even when the value is a literal.
    module_level_names = set(used_local_names)

    def _infer_ann(node: Any) -> tuple[cst.Annotation, set[str]]:
        """Infer a best-effort annotation for a libcst expression node.

        Returns (annotation_node, typing_names_required).
        The typing names set contains names like 'List', 'Dict', 'Tuple',
        'Set', 'Any', 'NamedTuple' when emitted annotations require imports.
        """
        typing_needed_local: set[str] = set()
        # simple scalars
        if isinstance(node, cst.SimpleString):
            return cst.Annotation(annotation=cst.Name("str")), typing_needed_local
        if isinstance(node, cst.Integer):
            return cst.Annotation(annotation=cst.Name("int")), typing_needed_local
        if isinstance(node, cst.Float):
            return cst.Annotation(annotation=cst.Name("float")), typing_needed_local
        if isinstance(node, cst.Name) and node.value in ("True", "False"):
            return cst.Annotation(annotation=cst.Name("bool")), typing_needed_local

        # List literal: try to infer homogeneous element type
        if isinstance(node, cst.List):
            elems = [getattr(e, "value", None) for e in node.elements or []]
            if elems:
                # infer each element and collect their annotation nodes and typing names
                inner_ann_nodes: list[cst.BaseExpression] = []
                for e in elems:
                    ann_e, names_e = (
                        _infer_ann(e) if e is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
                    )
                    # ann_e is an Annotation node; take its .annotation expression
                    inner_ann_nodes.append(ann_e.annotation)
                    typing_needed_local.update(names_e)
                # if all inner annotations are the same simple Name, use it as List[T]
                try:
                    inner_names = [
                        getattr(a, "value", None) if isinstance(a, cst.Name) else None for a in inner_ann_nodes
                    ]
                except Exception:
                    inner_names = [None for _ in inner_ann_nodes]
                if inner_names and all(n == inner_names[0] and n is not None for n in inner_names):
                    typing_needed_local.add("List")
                    return cst.Annotation(
                        annotation=cst.Subscript(
                            value=cst.Name("List"),
                            slice=[cst.SubscriptElement(slice=cst.Index(value=inner_ann_nodes[0]))],
                        )
                    ), typing_needed_local
            # fallback to List[Any]
            typing_needed_local.update({"List", "Any"})
            return cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("List"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ), typing_needed_local

        # Tuple literal: try to infer fixed heterogenous Tuple[...] when possible
        if isinstance(node, cst.Tuple):
            elems = [getattr(e, "value", None) for e in node.elements or []]
            if elems:
                ann_parts: list[cst.BaseExpression] = []
                for e in elems:
                    ann, names = (
                        _infer_ann(e) if e is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
                    )
                    ann_parts.append(ann.annotation)
                    typing_needed_local.update(names)
                # build Tuple[...]
                typing_needed_local.add("Tuple")
                subslices = [cst.SubscriptElement(slice=cst.Index(value=a)) for a in ann_parts]
                return cst.Annotation(
                    annotation=cst.Subscript(value=cst.Name("Tuple"), slice=subslices)
                ), typing_needed_local
            typing_needed_local.update({"Tuple", "Any"})
            return cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("Tuple"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ), typing_needed_local

        # Set literal
        if isinstance(node, cst.Set):
            elems = [getattr(e, "value", None) for e in node.elements or []]
            if elems:
                inner_ann, names = (
                    _infer_ann(elems[0])
                    if elems[0] is not None
                    else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
                )
                typing_needed_local.update(names)
                typing_needed_local.add("Set")
                return cst.Annotation(
                    annotation=cst.Subscript(
                        value=cst.Name("Set"), slice=[cst.SubscriptElement(slice=cst.Index(value=inner_ann.annotation))]
                    )
                ), typing_needed_local
            typing_needed_local.update({"Set", "Any"})
            return cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("Set"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ), typing_needed_local

        # Dict literal
        if isinstance(node, cst.Dict):
            elems = [e for e in node.elements or [] if isinstance(e, cst.DictElement)]
            if elems:
                k = getattr(elems[0], "key", None)
                v = getattr(elems[0], "value", None)
                k_ann, k_names = (
                    _infer_ann(k) if k is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
                )
                v_ann, v_names = (
                    _infer_ann(v) if v is not None else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
                )
                typing_needed_local.update(k_names)
                typing_needed_local.update(v_names)
                typing_needed_local.add("Dict")
                # Dict[K, V]
                return cst.Annotation(
                    annotation=cst.Subscript(
                        value=cst.Name("Dict"),
                        slice=[
                            cst.SubscriptElement(slice=cst.Index(value=k_ann.annotation)),
                            cst.SubscriptElement(slice=cst.Index(value=v_ann.annotation)),
                        ],
                    )
                ), typing_needed_local
            typing_needed_local.update({"Dict", "Any"})
            return cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("Dict"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ), typing_needed_local

        # Comprehensions and generator expressions: fallback to List[Any]
        # LibCST exposes several nodes; be defensive
        if getattr(cst, "ListComp", None) and isinstance(node, cst.ListComp):
            typing_needed_local.update({"List", "Any"})
            return cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("List"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ), typing_needed_local
        if getattr(cst, "GeneratorExp", None) and isinstance(node, cst.GeneratorExp):
            typing_needed_local.update({"List", "Any"})
            return cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("List"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                )
            ), typing_needed_local

        # Calls: Path-like constructors -> str, common factories list()/tuple()/set()/dict()
        if isinstance(node, cst.Call):
            fname = _get_callable_name(node.func)
            if fname and fname.endswith("Path"):
                return cst.Annotation(annotation=cst.Name("str")), typing_needed_local
            if fname in ("list", "tuple", "set"):
                # try to infer first arg
                if node.args:
                    inner = getattr(node.args[0], "value", None)
                    inner_ann, inner_names_set = (
                        _infer_ann(inner)
                        if inner is not None
                        else (cst.Annotation(annotation=cst.Name("Any")), {"Any"})
                    )
                    # inner_names_set is a set[str] returned by _infer_ann
                    typing_needed_local.update(inner_names_set)
                    typing_needed_local.add("List")
                    return cst.Annotation(
                        annotation=cst.Subscript(
                            value=cst.Name("List"),
                            slice=[cst.SubscriptElement(slice=cst.Index(value=inner_ann.annotation))],
                        )
                    ), typing_needed_local
                typing_needed_local.update({"List", "Any"})
                return cst.Annotation(
                    annotation=cst.Subscript(
                        value=cst.Name("List"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("Any")))]
                    )
                ), typing_needed_local
            if fname == "dict":
                typing_needed_local.add("Dict")
                return cst.Annotation(annotation=cst.Name("Dict")), typing_needed_local

        # fallback
        typing_needed_local.add("Any")
        return cst.Annotation(annotation=cst.Name("Any")), typing_needed_local

    def _get_callable_name(node: Any) -> Optional[str]:
        """Return a dotted name for simple Name/Attribute callables, or None.

        Examples: Name('Path') -> 'Path', Attribute(Name('pathlib'), Name('Path')) -> 'pathlib.Path'
        """
        if node is None:
            return None
        if isinstance(node, cst.Name):
            return node.value
        if isinstance(node, cst.Attribute):
            parts: list[str] = []
            cur: Any = node
            # unwind attributes defensively
            while isinstance(cur, cst.Attribute):
                if isinstance(getattr(cur, "attr", None), cst.Name):
                    parts.append(cur.attr.value)
                val = getattr(cur, "value", None)
                if isinstance(val, cst.Name):
                    parts.append(val.value)
                    break
                # prepare to unwrap further or bail
                cur = val
            return ".".join(reversed(parts)) if parts else None
        return None

    # read autocreate flag from pipeline context; default to True
    autocreate_flag = bool(context.get("autocreate", True)) if isinstance(context, dict) else True

    for cls_name, cls in out.classes.items():
        # Only synthesize a composite fixture in the specific case where
        # multiple attributes appear to be directory/path-like (e.g. temp
        # dirs) — otherwise prefer per-attribute fixtures which tests
        # expect. This avoids surprising bundling for simple attributes.
        attrs = list(getattr(cls, "setup_assignments", {}).keys())
        dir_like = sum(1 for a in attrs if "dir" in a or "path" in a)
        if len(attrs) > 1 and getattr(cls, "teardown_statements", None) and dir_like >= 2:
            # Heuristic name selection: prefer a pluralized 'dirs' fixture when
            # many attrs contain 'dir' or 'path', otherwise fallback to
            # `setup_<classname>`.
            attrs = list(cls.setup_assignments.keys())
            dir_like = sum(1 for a in attrs if "dir" in a or "path" in a)
            if dir_like >= 2:
                fixture_name = "temp_dirs"
            else:
                fixture_name = f"setup_{cls_name.lower()}"

            # Build local assignments for each attr using the last recorded
            # setup expression for that attribute.
            local_assignments: list[cst.BaseStatement] = []
            used_names_for_yield: list[tuple[str, str]] = []  # (key, localname)
            for attr in attrs:
                exprs = cls.setup_assignments.get(attr) or []
                # pick the last assignment expression if multiple
                value_expr = exprs[-1] if exprs else None
                # choose a safe local name (avoid collisions)
                base_local = attr
                local_name = base_local
                if local_name in used_local_names:
                    suffix = 1
                    while f"{local_name}_{suffix}" in used_local_names:
                        suffix += 1
                    local_name = f"{local_name}_{suffix}"
                used_local_names.add(local_name)

                if isinstance(value_expr, cst.BaseExpression):
                    assign_stmt = cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[cst.AssignTarget(target=cst.Name(local_name))],
                                value=value_expr,
                            )
                        ]
                    )
                    local_assignments.append(assign_stmt)
                # remember mapping for dict yield
                used_names_for_yield.append((attr, local_name))

            # create yield dict literal mapping string keys to local names
            dict_elements: list[cst.DictElement] = []
            for key, lname in used_names_for_yield:
                dict_elements.append(
                    cst.DictElement(key=cst.SimpleString(repr(key)), value=cst.Name(lname))
                )
            yield_expr = cst.Dict(elements=dict_elements)

            # rewrite cleanup statements to refer to local names instead of self.attr
            class _AttrRewriterMapping(cst.CSTTransformer):
                def __init__(self, mapping: dict[str, str]) -> None:
                    self.mapping = mapping

                def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
                    if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
                        if isinstance(original.attr, cst.Name):
                            attrn = original.attr.value
                            if attrn in self.mapping:
                                return cst.Name(self.mapping[attrn])
                    return updated

            mapping = {a: local for a, local in used_names_for_yield}
            safe_cleanup: list[cst.BaseStatement] = []
            for stmt in cls.teardown_statements:
                try:
                    new_stmt = cast(Any, stmt).visit(_AttrRewriterMapping(mapping))
                    safe_cleanup.append(new_stmt)
                except Exception:
                    # conservative: include original if rewrite fails
                    safe_cleanup.append(stmt)

            # build try/yield/finally block
            try_yield_block = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(yield_expr))])])
            finalblock_cst = cst.IndentedBlock(body=safe_cleanup or [])
            # Wrap the finally block in a cst.Finally node (libcst expects a Finally)
            try_finally = cst.Try(body=try_yield_block, handlers=[], orelse=None, finalbody=cst.Finally(body=finalblock_cst))

            # assemble function body: locals -> try/finally (append Try directly)
            body_stmts: list[cst.BaseStatement] = []
            body_stmts.extend(local_assignments)
            body_stmts.append(try_finally)
            body = cst.IndentedBlock(body=body_stmts)

            # ensure typing imports for Generator, Dict and Path
            all_typing_needed.update({"Generator", "Dict", "Path", "Any"})

            # Build a precise return annotation: Generator[Dict[str, Path], None, None]
            # Annotation AST: Generator[Dict[str, Path], None, None]
            # libcst representation: Subscript(Name('Generator'), [SubscriptElement(Index(Subscript(Name('Dict'), [SubscriptElement(Index(Name('str'))), SubscriptElement(Index(Name('Path')))]))), SubscriptElement(Index(Name('None'))), SubscriptElement(Index(Name('None')))])
            dict_inner = cst.Subscript(
                value=cst.Name("Dict"),
                slice=[
                    cst.SubscriptElement(slice=cst.Index(value=cst.Name("str"))),
                    cst.SubscriptElement(slice=cst.Index(value=cst.Name("Path"))),
                ],
            )
            gen_sub = cst.Subscript(
                value=cst.Name("Generator"),
                slice=[
                    cst.SubscriptElement(slice=cst.Index(value=dict_inner)),
                    cst.SubscriptElement(slice=cst.Index(value=cst.Name("None"))),
                    cst.SubscriptElement(slice=cst.Index(value=cst.Name("None"))),
                ],
            )

            return_ann = cst.Annotation(annotation=gen_sub)

            # create decorator and function def with precise return annotation
            decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
            func = cst.FunctionDef(name=cst.Name(fixture_name), params=cst.Parameters(), body=body, decorators=[decorator], returns=return_ann)
            fixture_nodes.append(func)
            # record a simple spec entry for completeness
            specs[fixture_name] = FixtureSpec(name=fixture_name, value_expr=None, cleanup_statements=safe_cleanup, yield_style=True)
            # skip per-attribute emission for this class
            continue
        # Detect composite helper-call patterns recorded in collector.local_assignments.
        # If multiple local names map to the same Call (tuple-unpack), and
        # corresponding attributes are assigned from those locals, synthesize
        # a single composite fixture that calls the helper and returns the
        # tuple, wiring upstream fixtures for any self.<attr> arguments.
        handled_attrs: Set[str] = set()
        try:
            # Build mapping from call source code -> list[(local_name, index, call_node)]
            call_groups: dict[str, list[tuple[str, Optional[int], Any]]] = {}
            for local_name, val in getattr(cls, "local_assignments", {}).items():
                # val is (assigned_value, maybe_index)
                assigned_call = None
                idx = None
                try:
                    assigned_call, idx = val
                except Exception:
                    assigned_call = val
                    idx = None
                if isinstance(assigned_call, cst.Call):
                    try:
                        # rendering a Call requires wrapping it into an Expr
                        key = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(assigned_call)])]).code
                    except Exception:
                        # fallback to repr-based key if rendering fails
                        key = repr(assigned_call)
                    call_groups.setdefault(key, []).append((local_name, idx, assigned_call))

            # For each group with multiple locals, check whether those locals
            # are later mapped into class attributes via setup_assignments
            for group in call_groups.values():
                if len(group) < 2:
                    continue
                # find which locals correspond to attributes
                local_to_attr: dict[str, str] = {}
                for local_name, idx, assigned_call in group:
                    # search for attributes whose value_expr references this local
                    for attr_name, assigns in cls.setup_assignments.items():
                        # take the last assignment as effective
                        v = assigns[-1] if isinstance(assigns, list) and assigns else assigns
                        # common pattern: self.attr = Name(local_name) or Call(Name(local_name))
                        # Match patterns where the attribute is assigned from a local name
                        # Direct name: self.attr = local_name
                        if isinstance(v, cst.Name) and v.value == local_name:
                            local_to_attr[local_name] = attr_name
                        # If the local variable name equals the attribute name, assume they correspond
                        # (covers patterns where the author rebinds or assigns literals to same-name attrs)
                        elif local_name == attr_name:
                            local_to_attr[local_name] = attr_name
                        # Call wrappers: self.attr = wrapper(local_name)
                        elif isinstance(v, cst.Call) and v.args:
                            for a in v.args:
                                a_val = getattr(a, "value", None)
                                if isinstance(a_val, cst.Name) and a_val.value == local_name:
                                    local_to_attr[local_name] = attr_name
                                    break
                if not local_to_attr:
                    continue

                # All right: synthesize composite fixture; prefer bundling into
                # a NamedTuple-based container and a single yield-style fixture
                # derived from the TestCase class name.
                assigned_call = group[0][2]

                # derive a container and fixture name from the TestCase class
                def _derive_names(class_name: str) -> tuple[str, str]:
                    base = class_name
                    if base.startswith("Test") and len(base) > 4:
                        base = base[4:]
                    if not base:
                        base = class_name
                    # NamedTuple name (private)
                    named = f"_{base}Data"
                    # fixture name: snake_case + _data
                    # Use a two-step regex to handle acronyms (e.g., API -> api)
                    import re

                    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", base)
                    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
                    fixture_nm = f"{snake}_data"
                    return named, fixture_nm

                namedtuple_name, fixture_name = _derive_names(cls_name)

                # ensure fixture_name doesn't collide with module-level names
                def _unique_name(base: str, taken: set[str]) -> str:
                    if base not in taken:
                        taken.add(base)
                        return base
                    i = 1
                    while True:
                        cand = f"{base}_{i}"
                        if cand not in taken:
                            taken.add(cand)
                            return cand
                        i += 1

                fixture_name = _unique_name(fixture_name, used_local_names)

                # prepare to emit NamedTuple definition and fixture
                # We'll collect required typing names into `typing_needed` and
                # accumulate them into `all_typing_needed` (declared outside the
                # class loop) so the centralized import injector stage can insert
                # a single `from typing import ...` line.
                typing_needed: set[str] = {"NamedTuple", "List", "Dict", "Any"}

                # determine upstream fixture parameters: collect referenced self.<name> attrs
                params: list[cst.Param] = []
                upstream_names: list[str] = []
                for arg in getattr(assigned_call, "args", []) or []:
                    a_val = getattr(arg, "value", None)
                    if (
                        isinstance(a_val, cst.Attribute)
                        and isinstance(getattr(a_val, "value", None), cst.Name)
                        and getattr(getattr(a_val, "value", None), "value", None) in ("self", "cls")
                    ):
                        aname = getattr(a_val.attr, "value", None)
                        if aname and aname not in upstream_names:
                            upstream_names.append(aname)
                            params.append(cst.Param(name=cst.Name(aname)))

                # prepare call expression with self.X replaced by bare names
                class _ReplaceSelf(cst.CSTTransformer):
                    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
                        if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
                            if isinstance(original.attr, cst.Name):
                                return cst.Name(original.attr.value)
                        return updated

                call_in_fixture = assigned_call.visit(_ReplaceSelf())

                # build tuple assignment target list in order of indices
                # sort group entries by index when present
                sorted_group = sorted(group, key=lambda x: (x[1] if x[1] is not None else 0))
                targets = [cst.Name(local) for local, _, _ in sorted_group]
                assign_target = cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Tuple(elements=[cst.Element(value=t) for t in targets]))],
                    value=call_in_fixture,
                )

                # Build NamedTuple fields and fixture body that constructs and yields it
                # Create class body: docstring + annotated assignments
                class_body: list[cst.BaseStatement] = []
                # docstring
                class_body.append(
                    cst.SimpleStatementLine(
                        body=[cst.Expr(cst.SimpleString('"""Container for test data and resources."""'))]
                    )
                )
                # fields: derive from local_to_attr mapping order
                for local, _, _ in sorted_group:
                    attr = local_to_attr.get(local)
                    # best-effort type: infer from recorded setup assignment if present
                    ann_node: cst.Annotation
                    orig_val = None
                    if attr:
                        setup_assigns: Optional[list[Any]] = cls.setup_assignments.get(attr)
                        if setup_assigns:
                            orig_val = setup_assigns[-1]
                    if orig_val is not None and isinstance(orig_val, cst.BaseExpression):
                        ann_node, names_needed = _infer_ann(orig_val)
                    else:
                        ann_node, names_needed = _infer_ann(None)
                    # collect typing names for this NamedTuple
                    for n in names_needed:
                        typing_needed.add(n)
                    ann_assign = cst.AnnAssign(
                        target=cst.Name(attr if attr else local), annotation=ann_node, value=None
                    )
                    class_body.append(cst.SimpleStatementLine(body=[ann_assign]))

                class_def = cst.ClassDef(
                    name=cst.Name(namedtuple_name),
                    bases=[cst.Arg(value=cst.Name("NamedTuple"))],
                    body=cst.IndentedBlock(body=class_body),
                )

                # fixture body: assign call result to locals, then yield container and finally cleanup
                assign_stmt = cst.SimpleStatementLine(body=[assign_target])
                # build TestData constructor call args
                ctor_args = []
                for local, _, _ in sorted_group:
                    attr = local_to_attr.get(local)
                    # preserve wrappers when present
                    orig_v: Optional[Any] = None
                    if attr:
                        setup_assigns = cls.setup_assignments.get(attr)
                        if setup_assigns:
                            orig_v = setup_assigns[-1]
                    if isinstance(orig_v, cst.Call) and orig_v.args:
                        new_call = orig_v.with_changes(args=[cst.Arg(value=cst.Name(local))])
                        ctor_args.append(cst.Arg(value=new_call))
                    else:
                        ctor_args.append(cst.Arg(value=cst.Name(local)))

                # build yield expression: yield NamedTupleName(field=...)
                ctor = cst.Call(func=cst.Name(namedtuple_name), args=ctor_args)
                yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(ctor))])

                # map teardown statements: rewrite self.attr -> local name
                rewritten_cleanup: list[cst.BaseStatement] = []
                for stmt in cls.teardown_statements:
                    new_stmt = cast(Any, stmt).visit(_ReplaceSelf())
                    rewritten_cleanup.append(new_stmt)

                # finally block: put cleanup statements
                finally_block = []
                for s in rewritten_cleanup:
                    finally_block.append(s)

                # construct try/finally as code: try: <assign>; yield; finally: <cleanup>
                if finally_block:
                    try_block = cst.Try(
                        body=cst.IndentedBlock(body=[assign_stmt, yield_stmt]),
                        handlers=[],
                        orelse=None,
                        finalbody=cst.Finally(body=cst.IndentedBlock(body=list(finally_block))),
                    )
                    body = cst.IndentedBlock(body=[try_block])
                    func = cst.FunctionDef(
                        name=cst.Name(fixture_name),
                        params=cst.Parameters(params=params),
                        body=body,
                        decorators=[
                            cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
                        ],
                    )
                else:
                    # no cleanup: simpler non-yield fixture that returns the container
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(ctor)])
                    body = cst.IndentedBlock(body=[assign_stmt, return_stmt])
                    func = cst.FunctionDef(
                        name=cst.Name(fixture_name),
                        params=cst.Parameters(params=params),
                        body=body,
                        decorators=[
                            cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
                        ],
                    )

                # aggregate typing names for later injection by import_injector
                all_typing_needed.update(typing_needed)
                # add class_def and fixture
                fixture_nodes.append(class_def)
                fixture_nodes.append(func)

                # mark attributes as handled so we skip generating per-attr fixtures
                for local_name in local_to_attr:
                    handled_attrs.add(local_to_attr[local_name])
        except Exception:
            # be conservative: on any unexpected shape, ignore and fall back
            handled_attrs = set()
        for attr, value in cls.setup_assignments.items():
            if attr in handled_attrs:
                # skip attributes already satisfied by a composite fixture
                continue
            # collector may record multiple assignments per attribute as a list
            multi_assigned = False
            if isinstance(value, list):
                multi_assigned = len(value) > 1
                # use the last assigned value as the effective value
                value_expr = value[-1] if value else None
            else:
                value_expr = value
            fname = f"{attr}"
            # If the recorded value is a self-referential placeholder (or a
            # simple wrapper like str(sql_file)) and the test author also
            # provided a sibling '<prefix>_content' assignment, auto-generate
            # a tmp_path-based fixture that writes that content to a file and
            # returns its string path. This avoids emitting broken
            # self-referential placeholders like `str(sql_file)` in fixtures.
            try:
                # conservative check: only for attrs that look like file names
                # and only if autocreate is enabled via CLI or API.
                if autocreate_flag and isinstance(attr, str) and attr.endswith("_file"):
                    prefix = attr[: -len("_file")]
                    candidate = f"{prefix}_content"
                    if candidate in cls.setup_assignments:
                        # attempt to infer filename from local assignments recorded
                        inferred_filename = None
                        # Collector may have recorded local assignments mapping names to (expr, index)
                        local_map = getattr(cls, "local_assignments", {}) or {}

                        def _get_callable_name(node: Any) -> Optional[str]:
                            """Return a dotted name for simple Name/Attribute callables, or None.

                            Examples: Name('Path') -> 'Path', Attribute(Name('pathlib'), Name('Path')) -> 'pathlib.Path'
                            """
                            if node is None:
                                return None
                            if isinstance(node, cst.Name):
                                return node.value
                            if isinstance(node, cst.Attribute):
                                parts: list[str] = []
                                cur: Any = node
                                # unwind attributes defensively
                                while isinstance(cur, cst.Attribute):
                                    if isinstance(getattr(cur, "attr", None), cst.Name):
                                        parts.append(cur.attr.value)
                                    val = getattr(cur, "value", None)
                                    if isinstance(val, cst.Name):
                                        parts.append(val.value)
                                        break
                                    # prepare to unwrap further or bail
                                    cur = val
                                return ".".join(reversed(parts)) if parts else None
                            return None

                        def _string_from_simple(aval: Any) -> Optional[str]:
                            if isinstance(aval, cst.SimpleString):
                                return aval.value.strip("\"'")
                            return None

                        def _find_filename_from_call(call: cst.Call) -> Optional[str]:
                            # 1) check keyword args commonly used for filenames
                            for arg in getattr(call, "args", []) or []:
                                # keyword may be Name (keyword arg) or None (positional)
                                kw = getattr(arg, "keyword", None)
                                if (
                                    kw
                                    and isinstance(kw, cst.Name)
                                    and kw.value.lower() in ("filename", "name", "path", "file")
                                ):
                                    sval = _string_from_simple(getattr(arg, "value", None))
                                    if sval:
                                        return sval
                            # 2) check positional args for a string literal-like filename
                            for arg in getattr(call, "args", []) or []:
                                sval = _string_from_simple(getattr(arg, "value", None))
                                if sval:
                                    return sval
                            # 3) check for Path(...) constructions: if the callee looks like Path
                            func_name = _get_callable_name(call.func)
                            if func_name and func_name.endswith("Path"):
                                for arg in getattr(call, "args", []) or []:
                                    sval = _string_from_simple(getattr(arg, "value", None))
                                    if sval:
                                        return sval
                            return None

                        # value_expr may be a Call wrapping a Name referencing a local var (e.g., str(sql_file))
                        target_name = None
                        if isinstance(value, list):
                            ve = value[-1] if value else None
                        else:
                            ve = value
                        if isinstance(ve, cst.Call) and ve.args:
                            for a in ve.args:
                                a_val = getattr(a, "value", None)
                                if isinstance(a_val, cst.Name):
                                    target_name = a_val.value
                                    break

                        # if we found a local assignment for that name, inspect its call args
                        if target_name and target_name in local_map:
                            assigned_call, index = local_map[target_name]
                            if isinstance(assigned_call, cst.Call):
                                inferred_filename = _find_filename_from_call(assigned_call)

                        # fallback filename if none inferred
                        if not inferred_filename:
                            inferred_filename = f"{attr}.sql"

                        # create autocreated fixture and skip normal fixture generation
                        fixture_node = create_autocreated_file_fixture(attr, candidate, filename=inferred_filename)
                        specs[fname] = FixtureSpec(
                            name=fname,
                            value_expr=value if not isinstance(value, list) else (value[-1] if value else None),
                            cleanup_statements=[],
                            yield_style=False,
                        )
                        fixture_nodes.append(fixture_node)
                        continue
            except Exception:
                # be conservative: fall back to normal behavior on unexpected shapes
                pass
            # find teardown statements that reference this attr
            # We accept a mix of libcst statement flavors here; widen to Any to
            # avoid variance and typeshed mismatches while preserving runtime
            # behavior. We'll narrow later at stage boundaries where needed.
            relevant_cleanup: list[Any] = []
            for stmt in cls.teardown_statements:
                # inspect common containers similarly to legacy
                def _stmt_references(s: Any) -> bool:
                    # SimpleStatementLine: inspect expr or assign
                    if isinstance(s, cst.SimpleStatementLine) and s.body:
                        expr = s.body[0]
                        # assignment
                        if isinstance(expr, cst.Assign):
                            for t in expr.targets:
                                target = getattr(t, "target", t)
                                if _references_attribute(target, attr):
                                    return True
                            if _references_attribute(expr.value, attr):
                                return True
                        # expression wrapper (e.g., Expr(Call(...)))
                        if isinstance(expr, cst.Expr):
                            if _references_attribute(expr.value, attr):
                                return True
                        # delete statements: del self.attr
                        # Some libcst versions/typeshed don't expose a Delete symbol
                        # that mypy recognizes. Detect by class name to avoid mypy errors.
                        cls = getattr(expr, "__class__", None)
                        if cls is not None and getattr(cls, "__name__", None) == "Delete":
                            for t in getattr(expr, "targets", []):
                                target = getattr(t, "target", t)
                                if _references_attribute(target, attr):
                                    return True
                    # If/IndentedBlock: inspect body and orelse
                    if isinstance(s, cst.If):
                        if _references_attribute(s.test, attr):
                            return True
                        for inner in getattr(s.body, "body", []):
                            if _stmt_references(inner):
                                return True
                        orelse = getattr(s, "orelse", None)
                        if orelse:
                            if isinstance(orelse, cst.IndentedBlock):
                                for inner in getattr(orelse, "body", []):
                                    if _stmt_references(inner):
                                        return True
                            elif isinstance(orelse, cst.If):
                                if _stmt_references(orelse):
                                    return True
                    # IndentedBlock
                    if isinstance(s, cst.IndentedBlock):
                        for inner in getattr(s, "body", []):
                            if _stmt_references(inner):
                                return True
                    return False

                try:
                    if _stmt_references(stmt):
                        # cast to the wider union to satisfy list element typing
                        relevant_cleanup.append(stmt)
                except Exception:
                    # be conservative: ignore unexpected shapes
                    pass

            # fallback: if our structural checks missed some unusual Delete/cleanup
            # forms, conservatively include statements whose rendered code contains
            # both 'del' and the attribute name. This mirrors the legacy transformer's
            # tolerant behavior and avoids missing cleanup like 'del self.x'.
            if not relevant_cleanup:
                for stmt in cls.teardown_statements:
                    try:
                        rendered = cst.Module(body=[stmt]).code
                        if "del" in rendered and (f"self.{attr}" in rendered or f"{attr}" in rendered):
                            relevant_cleanup.append(stmt)
                    except Exception:
                        # ignore rendering issues; keep conservative behavior
                        pass

            has_cleanup = bool(relevant_cleanup)
            yield_style = has_cleanup
            spec = FixtureSpec(
                name=fname, value_expr=value_expr, cleanup_statements=relevant_cleanup.copy(), yield_style=yield_style
            )
            specs[fname] = spec
            # infer typing requirements from the recorded value expression so
            # import_injector can insert needed typing imports even for
            # non-composite fixtures (e.g., list/dict/set literals)
            try:
                ann_infer, names_req = (
                    _infer_ann(value_expr) if isinstance(value_expr, cst.BaseExpression) else _infer_ann(None)
                )
                for n in names_req:
                    all_typing_needed.add(n)
            except Exception:
                # be conservative: ignore inference failures
                pass
            # create a minimal fixture node: @pytest.fixture
            decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))

            # determine local name and ensure uniqueness
            def _choose_local_name(base: str, taken: set[str]) -> str:
                """Deterministically pick a unique local name by appending
                a numeric suffix when needed. Returns the chosen name and
                reserves it in `taken`.
                """
                if base not in taken:
                    taken.add(base)
                    return base
                suffix = 1
                while True:
                    candidate = f"{base}_{suffix}"
                    if candidate not in taken:
                        taken.add(candidate)
                        return candidate
                    suffix += 1

            base_local = f"_{attr}_value"
            local_name = _choose_local_name(base_local, used_local_names)
            spec.local_value_name = local_name

            # decide whether to bind to a local variable or return the value
            # directly. For non-yield fixtures where the value is a simple
            # literal, container literal, or comprehension, return the value
            # directly to produce a canonical simple fixture form. Otherwise,
            # bind to a unique local name so cleanup rewrites can reference it.
            def _is_simple_value(expr: Any) -> bool:
                if expr is None:
                    return False
                # simple scalar literals
                if isinstance(expr, (cst.Integer, cst.Float, cst.Imaginary, cst.SimpleString, cst.Name)):
                    return True
                # container literals
                if isinstance(expr, (cst.List, cst.Tuple, cst.Set, cst.Dict)):
                    return True
                # comprehensions
                cls = getattr(expr, "__class__", None)
                if cls is not None and getattr(cls, "__name__", "").endswith("Comp"):
                    return True
                return False

            # previously we used local temporaries here; they were removed
            # to avoid unused-variable lints. The direct-return decision is
            # performed in-place where needed.

            # helper rewriter to replace self.attr or cls.attr with local_name
            class _AttrRewriterTarget(cst.CSTTransformer):
                def __init__(self, target_attr: str, local: str) -> None:
                    self.target_attr = target_attr
                    self.local = local

                def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
                    if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
                        if isinstance(original.attr, cst.Name) and original.attr.value == self.target_attr:
                            return cst.Name(self.local)
                    return updated

            # body: return or yield
            # skip creating fixture if a top-level function with same name already exists
            if module is not None and any(
                isinstance(n, cst.FunctionDef) and n.name.value == fname for n in module.body
            ):
                # still record spec but don't create a duplicate fixture node
                specs[fname] = spec
                continue

            if yield_style:
                # If the value is a simple literal and all cleanup statements are
                # simple assignments or deletions targeting the attribute, we
                # can yield the literal directly and rewrite cleanup to use the
                # fixture name (e.g., value = None). Otherwise, bind to a
                # unique local name and rewrite cleanup to reference that
                # local name so complex control flow works safely.
                def _is_simple_cleanup_statement(s: Any) -> bool:
                    # Simple assignment like `self.attr = X` or `del self.attr`
                    if isinstance(s, cst.SimpleStatementLine) and s.body:
                        expr = s.body[0]
                        if isinstance(expr, cst.Assign):
                            target = expr.targets[0].target
                            if (
                                isinstance(target, cst.Attribute)
                                and isinstance(target.value, cst.Name)
                                and target.value.value in ("self", "cls")
                            ):
                                return True
                        # Some libcst versions/typeshed don't expose a Delete symbol
                        # that mypy recognizes. Detect Delete by class name to avoid
                        # mypy attr-defined errors.
                        cls = getattr(expr, "__class__", None)
                        if cls is not None and getattr(cls, "__name__", None) == "Delete":
                            for t in getattr(expr, "targets", []):
                                targ = getattr(t, "target", t)
                                if (
                                    isinstance(targ, cst.Attribute)
                                    and isinstance(getattr(targ, "value", None), cst.Name)
                                    and getattr(getattr(targ, "value", None), "value", None) in ("self", "cls")
                                ):
                                    return True
                    return False

                # If multiple assignments occurred in setUp, prefer binding to a
                # local name so cleanup rewrites are consistent and literal-only
                # yields are avoided. Also, if the module already defines the
                # conventional local base name (e.g., `_x_value`), force binding
                # to avoid colliding with module-level identifiers.
                # Force binding if module defines the conventional local name
                # or if the module contains private/underscore-prefixed names
                # (common pattern) which increases risk of collision with
                # the conventional fixture-local names like `_x_value`.
                force_bind_due_to_module_collision = base_local in module_level_names or any(
                    name and name.startswith("_") for name in module_level_names
                )
                if (
                    not multi_assigned
                    and _is_literal(value_expr)
                    and all(_is_simple_cleanup_statement(s) for s in spec.cleanup_statements)
                    and not force_bind_due_to_module_collision
                ):
                    # yield the literal value and rewrite cleanup to use fixture name
                    yield_stmt = cst.SimpleStatementLine(
                        body=[cst.Expr(cst.Yield(cast(cst.BaseExpression, value_expr)))]
                    )
                    # accumulate as Any to accept mixed libcst statement flavors
                    body_stmts_small_small: List[Any] = [yield_stmt]
                    for stmt in spec.cleanup_statements:
                        new_stmt = cast(Any, stmt).visit(_AttrRewriterTarget(attr, fname))
                        body_stmts_small_small.append(new_stmt)
                    # IndentedBlock expects Sequence[BaseStatement]; widen types here
                    body = cst.IndentedBlock(body=list(cast(Sequence[cst.BaseStatement], body_stmts_small_small)))
                    func = cst.FunctionDef(
                        name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator]
                    )
                    fixture_nodes.append(func)
                else:
                    # bind to local_name and yield it; rewrite cleanup to local_name
                    # create assignment to local_name then yield it
                    assign_stmt = cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[cst.AssignTarget(target=cst.Name(local_name))],
                                value=cast(cst.BaseExpression, value_expr),
                            )
                        ]
                    )
                    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(cst.Name(local_name)))])
                    # accumulate as Any to accept Assign (BaseStatement) and
                    # SimpleStatementLine/other small-statement flavors
                    body_stmts_small_small = [assign_stmt, yield_stmt]
                    for stmt in spec.cleanup_statements:
                        new_stmt = cast(Any, stmt).visit(_AttrRewriterTarget(attr, local_name))
                        body_stmts_small_small.append(new_stmt)
                    body = cst.IndentedBlock(body=list(cast(Sequence[cst.BaseStatement], body_stmts_small_small)))
                    func = cst.FunctionDef(
                        name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator]
                    )
                    fixture_nodes.append(func)
            else:
                # For simple literal values, return the literal directly instead
                # of binding to a local name, preserving the original intent
                # (e.g., return 42). For ambiguous self-referential expressions,
                # delegate to guarded simple fixture creation to avoid broken
                # placeholders like `str(schema_file)`.
                # Treat simple scalars and literal containers/comprehensions as
                # candidates for emitting a concrete return annotation.
                is_container_literal = isinstance(value_expr, (cst.List, cst.Tuple, cst.Set, cst.Dict))
                is_comp = getattr(cst, "ListComp", None) and isinstance(value_expr, getattr(cst, "ListComp"))
                if _is_literal(value_expr) or is_container_literal or is_comp:
                    # infer return annotation for the literal container/value
                    # infer return annotation for the literal container/value
                    ann: Optional[cst.Annotation]
                    ann = None
                    try:
                        ann_res, names_req = _infer_ann(
                            value_expr if isinstance(value_expr, cst.BaseExpression) else None
                        )
                        ann = ann_res
                        for n in names_req:
                            all_typing_needed.add(n)
                    except Exception:
                        ann = None
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(cast(cst.BaseExpression, value_expr))])
                    body = cst.IndentedBlock(body=[return_stmt])
                    if ann is not None:
                        func = cst.FunctionDef(
                            name=cst.Name(fname),
                            params=cst.Parameters(),
                            returns=ann,
                            body=body,
                            decorators=[decorator],
                        )
                    else:
                        func = cst.FunctionDef(
                            name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator]
                        )
                    fixture_nodes.append(func)
                else:
                    # Use guarded simple fixture creator which detects self-referential placeholders
                    guarded = create_simple_fixture_with_guard(fname, cast(cst.BaseExpression, value_expr))
                    fixture_nodes.append(guarded)
    result: dict[str, Any] = {"fixture_specs": specs, "fixture_nodes": fixture_nodes}
    if all_typing_needed:
        result["needs_typing_names"] = sorted(all_typing_needed)
    return result
