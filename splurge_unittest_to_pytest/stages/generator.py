"""FixtureGenerator stage: produce FixtureSpec entries and cst.FunctionDef fixture nodes
from CollectorOutput.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


@dataclass
class FixtureSpec:
    name: str
    value_expr: cst.BaseExpression
    cleanup_statements: List[cst.BaseStatement]
    yield_style: bool
    local_value_name: Optional[str] = None


def _is_literal(expr: cst.BaseExpression) -> bool:
    return isinstance(expr, (cst.Integer, cst.Float, cst.SimpleString, cst.Name))


def generator_stage(context: dict) -> dict:
    out: CollectorOutput = context.get("collector_output")
    if out is None:
        return {}
    specs: Dict[str, FixtureSpec] = {}
    fixture_nodes: List[cst.FunctionDef] = []
    used_local_names: set[str] = set()
    # populate used_local_names from module-level identifiers to avoid collisions
    module: cst.Module | None = context.get("module")
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

    for cls_name, cls in out.classes.items():
        for attr, value in cls.setup_assignments.items():
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
                        if isinstance(expr, cst.Delete):
                            # Delete.targets is a list of targets (like Assign.targets)
                            for t in expr.targets:
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
            spec = FixtureSpec(name=fname, value_expr=value, cleanup_statements=relevant_cleanup.copy(), yield_style=yield_style)
            specs[fname] = spec
            # create a minimal fixture node: @pytest.fixture
            decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
            # determine local name and ensure uniqueness
            base_local = f"_{attr}_value"
            local_name = base_local
            suffix = 1
            while local_name in used_local_names:
                suffix += 1
                local_name = f"{base_local}_{suffix}"
            used_local_names.add(local_name)
            spec.local_value_name = local_name

            # bind value to local variable in all cases to make cleanup rewriting consistent
            assign = cst.SimpleStatementLine(body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name(local_name))], value=value)])

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
                # yield the local name
                yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(cst.Name(local_name)))])
                # transform cleanup statements to reference the local name instead of self.attr
                body_stmts = [assign, yield_stmt]
                for stmt in spec.cleanup_statements:
                    new_stmt = stmt.visit(_AttrRewriter(attr, local_name))
                    body_stmts.append(new_stmt)
                body = cst.IndentedBlock(body=body_stmts)
                func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                fixture_nodes.append(func)
            else:
                # non-yield: return the local name
                return_stmt = cst.SimpleStatementLine(body=[cst.Return(cst.Name(local_name))])
                body = cst.IndentedBlock(body=[assign, return_stmt])
                func = cst.FunctionDef(name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator])
                fixture_nodes.append(func)
    return {"fixture_specs": specs, "fixture_nodes": fixture_nodes}
