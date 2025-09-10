"""FixtureGenerator stage: produce FixtureSpec entries and cst.FunctionDef fixture nodes
from CollectorOutput.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, cast

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


@dataclass
class FixtureSpec:
    name: str
    # value_expr can legitimately be None when collector recorded no value
    value_expr: Optional[cst.BaseExpression]
    cleanup_statements: List[cst.BaseStatement]
    yield_style: bool
    local_value_name: Optional[str] = None


def _is_literal(expr: Optional[cst.BaseExpression]) -> bool:
    if expr is None:
        return False
    return isinstance(expr, (cst.Integer, cst.Float, cst.SimpleString, cst.Name))


def generator_stage(context: Dict[str, Any]) -> Dict[str, Any]:
    maybe_out: Any = context.get("collector_output")
    out: Optional[CollectorOutput] = maybe_out if isinstance(maybe_out, CollectorOutput) else None
    if out is None:
        return {}
    specs: Dict[str, FixtureSpec] = {}
    fixture_nodes: List[cst.FunctionDef] = []
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
            # imports
            if isinstance(node, cst.SimpleStatementLine):
                for stmt in node.body:
                    if isinstance(stmt, cst.Import):
                        for name in stmt.names:
                            asname = name.asname
                            if asname and isinstance(asname.name, cst.Name):
                                used_local_names.add(asname.name.value)
                            else:
                                used_local_names.add(name.name.value.split(".")[0])
                    if isinstance(stmt, cst.ImportFrom):
                        for name in stmt.names or []:
                            asname = name.asname
                            if asname and isinstance(asname.name, cst.Name):
                                used_local_names.add(asname.name.value)
                            else:
                                used_local_names.add(name.name.value if isinstance(name.name, str) else getattr(name.name, 'value', None))
    def _references_attribute(expr: cst.BaseExpression | None, attr_name: str) -> bool:
        """Recursively check if expression references self.<attr> or bare <attr>.

        This mirrors the legacy converter's conservative search used to decide
        whether a teardown statement references a given setup attribute.
        """
        if expr is None:
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
                inner = getattr(s, 'slice', None) or getattr(s, 'value', None) or s
                if isinstance(inner, cst.BaseExpression) and _references_attribute(inner, attr_name):
                    return True
            return False
        # Binary/Comparison/Boolean ops
        if isinstance(expr, (cst.BinaryOperation, cst.Comparison, cst.BooleanOperation)):
            parts: list[cst.BaseExpression] = []
            if hasattr(expr, 'left'):
                parts.append(expr.left)  # type: ignore[attr-defined]
            if hasattr(expr, 'right'):
                parts.append(expr.right)  # type: ignore[attr-defined]
            if hasattr(expr, 'comparisons'):
                for comp in expr.comparisons:  # type: ignore[attr-defined]
                    comp_item = getattr(comp, 'comparison', None) or getattr(comp, 'operator', None)
                    if comp_item is not None and isinstance(comp_item, cst.BaseExpression):
                        parts.append(comp_item)
            for p in parts:
                if _references_attribute(p, attr_name):
                    return True
            return False
        # Tuples/Lists/Sets
        if isinstance(expr, (cst.Tuple, cst.List, cst.Set)):
            for e in expr.elements:
                val = getattr(e, 'value', e)
                if isinstance(val, cst.BaseExpression) and _references_attribute(val, attr_name):
                    return True
            return False

    # snapshot module-level names to detect collisions that should force
    # binding to a local name even when the value is a literal.
    module_level_names = set(used_local_names)

    for cls_name, cls in out.classes.items():
        for attr, value in cls.setup_assignments.items():
            # collector may record multiple assignments per attribute as a list
            multi_assigned = False
            if isinstance(value, list):
                multi_assigned = len(value) > 1
                # use the last assigned value as the effective value
                value_expr = value[-1] if value else None
            else:
                value_expr = value
            fname = f"{attr}"
            # find teardown statements that reference this attr
            relevant_cleanup: list[cst.BaseStatement] = []
            for stmt in cls.teardown_statements:
                # inspect common containers similarly to legacy
                def _stmt_references(s: cst.BaseStatement) -> bool:
                    # SimpleStatementLine: inspect expr or assign
                    if isinstance(s, cst.SimpleStatementLine) and s.body:
                        expr = s.body[0]
                        # assignment
                        if isinstance(expr, cst.Assign):
                            for t in expr.targets:
                                target = getattr(t, 'target', t)
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
                        if getattr(expr, "__class__", None).__name__ == "Delete":
                            for t in getattr(expr, 'targets', []):
                                target = getattr(t, 'target', t)
                                if _references_attribute(target, attr):
                                    return True
                    # If/IndentedBlock: inspect body and orelse
                    if isinstance(s, cst.If):
                        if _references_attribute(s.test, attr):
                            return True
                        for inner in getattr(s.body, 'body', []):
                            if _stmt_references(inner):
                                return True
                        orelse = getattr(s, 'orelse', None)
                        if orelse:
                            if isinstance(orelse, cst.IndentedBlock):
                                for inner in getattr(orelse, 'body', []):
                                    if _stmt_references(inner):
                                        return True
                            elif isinstance(orelse, cst.If):
                                if _stmt_references(orelse):
                                    return True
                    # IndentedBlock
                    if isinstance(s, cst.IndentedBlock):
                        for inner in getattr(s, 'body', []):
                            if _stmt_references(inner):
                                return True
                    return False

                try:
                    if _stmt_references(stmt):
                        relevant_cleanup.append(cast(cst.BaseStatement, stmt))
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
            spec = FixtureSpec(name=fname, value_expr=value_expr, cleanup_statements=relevant_cleanup.copy(), yield_style=yield_style)
            specs[fname] = spec
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

            # bind value to local variable in all cases to make cleanup rewriting consistent
            # libcst.Assign.value expects a BaseExpression; value_expr may be None
            assign = cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[cst.AssignTarget(target=cst.Name(local_name))],
                        value=cast(cst.BaseExpression, value_expr),
                    )
                ]
            )

            # helper rewriter to replace self.attr or cls.attr with local_name
            class _AttrRewriter(cst.CSTTransformer):
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
            if module is not None and any(isinstance(n, cst.FunctionDef) and n.name.value == fname for n in module.body):
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
                def _is_simple_cleanup_statement(s: cst.BaseStatement) -> bool:
                    # Simple assignment like `self.attr = X` or `del self.attr`
                    if isinstance(s, cst.SimpleStatementLine) and s.body:
                        expr = s.body[0]
                        if isinstance(expr, cst.Assign):
                            target = expr.targets[0].target
                            if isinstance(target, cst.Attribute) and isinstance(target.value, cst.Name) and target.value.value in ("self", "cls"):
                                return True
                        if isinstance(expr, cst.Delete):
                            for t in expr.targets:
                                targ = getattr(t, 'target', t)
                                if isinstance(targ, cst.Attribute) and isinstance(targ.value, cst.Name) and targ.value.value in ("self", "cls"):
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
                force_bind_due_to_module_collision = (
                    base_local in module_level_names
                    or any(name and name.startswith("_") for name in module_level_names)
                )
                if (not multi_assigned and _is_literal(value_expr) and all(_is_simple_cleanup_statement(s) for s in spec.cleanup_statements)
                        and not force_bind_due_to_module_collision):
                    # yield the literal value and rewrite cleanup to use fixture name
                    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(cast(cst.BaseExpression, value_expr)))])
                    body_stmts = [yield_stmt]
                    for stmt in spec.cleanup_statements:
                        new_stmt = stmt.visit(_AttrRewriter(attr, fname))
                        body_stmts.append(new_stmt)
                    body = cst.IndentedBlock(body=body_stmts)
                    func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                    fixture_nodes.append(func)
                else:
                    # bind to local_name and yield it; rewrite cleanup to local_name
                    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(cst.Name(local_name)))])
                    body_stmts = [assign, yield_stmt]
                    for stmt in spec.cleanup_statements:
                        new_stmt = stmt.visit(_AttrRewriter(attr, local_name))
                        body_stmts.append(new_stmt)
                    body = cst.IndentedBlock(body=body_stmts)
                    func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                    fixture_nodes.append(func)
            else:
                # For simple literal values, return the literal directly instead
                # of binding to a local name, preserving the original intent
                # (e.g., return 42). For non-literals we still bind to a local
                # name and return it to keep cleanup rewriting consistent.
                if _is_literal(value_expr):
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(cast(cst.BaseExpression, value_expr))])
                    body = cst.IndentedBlock(body=[return_stmt])
                    func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                    fixture_nodes.append(func)
                else:
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(cst.Name(local_name))])
                    body = cst.IndentedBlock(body=[assign, return_stmt])
                    func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                    fixture_nodes.append(func)
    return {"fixture_specs": specs, "fixture_nodes": fixture_nodes}
