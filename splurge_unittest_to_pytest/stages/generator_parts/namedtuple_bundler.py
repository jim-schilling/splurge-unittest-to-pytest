"""Group related local assignments into a NamedTuple-like container.

Find local assignments that originate from the same call site, emit a
light container class (modeled after NamedTuple) and a paired composite
fixture that constructs and yields instances of that container. The
extraction makes bundling logic unit-testable.

Publics:
    bundle_named_locals
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import libcst as cst

DOMAINS = ["generator", "bundles"]

# Associated domains for this module


def bundle_named_locals(
    out_classes: Dict[str, Any], existing_top_names: Set[str]
) -> Tuple[List[cst.BaseStatement], Set[str], Dict[str, str]]:
    """Group related local assignments into a bundled NamedTuple fixture.

    Returns (nodes, needs_typing, attr_to_fixture) where ``nodes`` contains
    the emitted class and fixture nodes, ``needs_typing`` lists typing names
    required, and ``attr_to_fixture`` maps attribute names to fixture names.
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
            # Collect simple Name dependencies from the call so the emitted
            # composite fixture can accept and receive underlying fixtures
            # (e.g., temp_dir, sql_content) as parameters. We conservatively
            # filter out self/cls, builtins, capitalized names, and any
            # existing top-level module names to avoid collisions.
            try:

                class _NameCollector(cst.CSTVisitor):
                    def __init__(self) -> None:
                        self.names: set[str] = set()

                    def visit_Name(self, node: cst.Name) -> None:
                        self.names.add(node.value)

                nc = _NameCollector()
                call_in_fixture.visit(nc)
                collected = set(getattr(nc, "names", set()))
            except Exception:
                collected = set()

            # Expand names that correspond to recorded local assignments to
            # include their RHS refs (e.g., local sql_file -> temp_dir, sql_content)
            expanded: set[str] = set()
            import builtins as _builtins

            for n in collected:
                if not n or n in ("self", "cls"):
                    continue
                if n in existing_top_names:
                    continue
                if n[0].isupper():
                    continue
                if n in getattr(_builtins, "__dict__", {}):
                    continue
                # If name matches a local assignment, expand to its recorded refs
                if n in local_map:
                    try:
                        entry = local_map.get(n)
                        if isinstance(entry, tuple) and len(entry) >= 3:
                            refs_from_local = entry[2] or set()
                            for r in refs_from_local:
                                expanded.add(r)
                            continue
                    except Exception:
                        pass
                expanded.add(n)

            # Deterministic ordering for parameters
            param_names = [r for r in sorted(expanded)]
            if param_names:
                params = cst.Parameters(params=[cst.Param(name=cst.Name(n)) for n in param_names])
            else:
                params = cst.Parameters()
            targets = [cst.Name(local) for local, _, _ in sorted_group]
            assign_target = cst.Assign(
                targets=[cst.AssignTarget(target=cst.Tuple(elements=[cst.Element(value=t) for t in targets]))],
                value=call_in_fixture,
            )
            assign_stmt = cst.SimpleStatementLine(body=[assign_target])

            # Build constructor args for the NamedTuple. If the original
            # class setup assigned the attribute using a transformation
            # (for example: `self.sql_file = str(sql_file)`), preserve
            # that transformation in the emitted fixture by using the
            # recorded setup assignment expression (with `self.`/`cls.`
            # replaced by bare names) so the NamedTuple yields the same
            # shaped values (e.g., strings instead of Path objects).
            ctor_args_list: list[cst.Arg] = []
            for local, _, _ in sorted_group:
                # default expression is the bare local name
                expr: cst.BaseExpression = cst.Name(local)
                # If this local mapped to an attribute and that attribute
                # had a recorded setup assignment (like `self.x = str(local)`),
                # use that expression instead (after removing `self.`).
                attr = local_to_attr.get(local, local)
                setup_assigns = getattr(cls, "setup_assignments", {}) or {}
                if attr in setup_assigns:
                    v = setup_assigns[attr]
                    # v may be a list of assignments; prefer the last one
                    if isinstance(v, list) and v:
                        v = v[-1]
                    try:
                        # If the setup assignment is a simple Name that
                        # references a recorded local assignment, prefer
                        # the RHS from local_map so we preserve the
                        # original transformation (e.g., str(sql_file)).
                        if isinstance(v, cst.Name) and getattr(v, "value", None) in local_map:
                            entry = local_map.get(v.value)
                            if isinstance(entry, tuple) and len(entry) >= 1:
                                rhs = entry[0]
                                idx_from_local = entry[1] if len(entry) > 1 else None
                                transformed = rhs.visit(_ReplaceSelfLocal())
                                if idx_from_local is None:
                                    if isinstance(transformed, cst.BaseExpression):
                                        expr = transformed
                                else:
                                    # tuple-unpacked local: index into the call
                                    try:
                                        expr = cst.Subscript(
                                            value=transformed,
                                            slice=[
                                                cst.SubscriptElement(
                                                    slice=cst.Index(value=cst.Integer(str(idx_from_local)))
                                                )
                                            ],
                                        )
                                    except Exception:
                                        expr = cst.Name(local)
                        else:
                            # reuse the same ReplaceSelfLocal logic to strip
                            # `self.`/`cls.` prefixes from attribute expressions
                            transformed = v.visit(_ReplaceSelfLocal())
                            if isinstance(transformed, cst.BaseExpression):
                                expr = transformed
                    except Exception:
                        # fall back to bare local name on any error
                        expr = cst.Name(local)
                ctor_args_list.append(cst.Arg(value=expr))
            ctor_args = ctor_args_list
            ctor = cst.Call(func=cst.Name(namedtuple_name), args=ctor_args)
            yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(ctor))])
            decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
            body = cst.IndentedBlock(body=[assign_stmt, yield_stmt])
            fixture_func = cst.FunctionDef(
                name=cst.Name(fixture_name), params=params, body=body, decorators=[decorator]
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
