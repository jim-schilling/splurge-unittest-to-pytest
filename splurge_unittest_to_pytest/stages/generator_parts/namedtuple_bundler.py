"""Bundle local assignments into NamedTuple containers and emit fixtures.

This module extracts the NamedTuple-bundling logic from the large
`stages/generator.py` file so it can be unit-tested in isolation.

Public API:
    bundle_named_locals(out_classes, existing_top_names) -> tuple[list[cst.BaseStatement], set[str]]

The function returns (fixture_nodes_to_prepend, typing_names_required).
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import libcst as cst


def bundle_named_locals(
    out_classes: Dict[str, Any], existing_top_names: Set[str]
) -> Tuple[List[cst.BaseStatement], Set[str], Dict[str, str]]:
    """Collect groups of local_assignments that should be bundled into a
    NamedTuple and a single bundled fixture. Returns a list of nodes (class
    def + fixture def) to prepend and a set of typing names required.

    This mirrors the original generator bundling heuristics: group locals
    produced by the same Call and where multiple locals map to attributes.
    """
    fixture_nodes: List[cst.BaseStatement] = []
    needs_typing: Set[str] = set()
    used_names: Set[str] = set()
    # Map attribute name -> bundled fixture name (e.g., sql_file -> init_api_data)
    attr_to_fixture: Dict[str, str] = {}

    for cls_name, cls in out_classes.items():
        local_map = getattr(cls, "local_assignments", {}) or {}
        # group by textual representation of the assigned call
        # Use flexible Any tuple element types to avoid tight mypy tuple shape
        # assumptions - values may include optional index and Call nodes.
        call_groups: dict[str, list[tuple[str, Any, Any]]] = {}
        for local_name, val in local_map.items():
            # support stored tuples of shape (call, idx) or (call, idx, refs)
            if isinstance(val, tuple) or isinstance(val, list):
                assigned_call = val[0]
                idx = val[1] if len(val) > 1 else None
            else:
                assigned_call = val
                idx = None
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
            # map locals to attributes
            local_to_attr: Dict[str, str] = {}
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

            # derive container and fixture names from class name
            def _derive_names(class_name: str) -> Tuple[str, str]:
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
            # uniqueness checks
            if namedtuple_name in used_names or namedtuple_name in existing_top_names:
                continue
            used_names.add(namedtuple_name)
            if fixture_name in existing_top_names:
                suffix_i = 1
                base = fixture_name
                while f"{base}_{suffix_i}" in existing_top_names:
                    suffix_i += 1
                fixture_name = f"{base}_{suffix_i}"

            class_body: List[cst.BaseStatement] = []
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

            assigned_call = group[0][2]

            # replace self.* with bare names when embedding the call
            class _ReplaceSelfLocal(cst.CSTTransformer):
                def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
                    if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
                        if isinstance(original.attr, cst.Name):
                            return cst.Name(original.attr.value)
                    return updated

            call_in_fixture = assigned_call.visit(_ReplaceSelfLocal())
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

            # append in discovered order to preserve stable emission order
            fixture_nodes.append(class_def)
            fixture_nodes.append(fixture_func)
            # record which attributes were bundled into this composite fixture
            for local, _, _ in sorted_group:
                attr_name = local_to_attr.get(local, local)
                attr_to_fixture[attr_name] = fixture_name
            try:
                needs_typing.update({"NamedTuple", "Any"})
            except Exception:
                pass

    return fixture_nodes, needs_typing, attr_to_fixture
