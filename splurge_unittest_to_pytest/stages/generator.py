"""FixtureGenerator stage: produce FixtureSpec entries and cst.FunctionDef fixture nodes
from CollectorOutput.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Set, cast, Sequence

import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.namedtuple_bundler import bundle_named_locals
from splurge_unittest_to_pytest.stages.generator_parts.self_attr_finder import collect_self_attrs
from splurge_unittest_to_pytest.stages.generator_parts.literals import is_literal
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


@dataclass
class FixtureSpec:
    name: str
    # value_expr can legitimately be None when collector recorded no value
    value_expr: Optional[cst.BaseExpression]
    cleanup_statements: list[Any]
    yield_style: bool
    local_value_name: Optional[str] = None


def _is_literal(expr: Optional[cst.BaseExpression]) -> bool:
    # keep a thin wrapper to avoid changing existing call sites in this file
    return is_literal(expr)


def generator_stage(context: dict[str, Any]) -> dict[str, Any]:
    maybe_out: Any = context.get("collector_output")
    out: Optional[CollectorOutput] = maybe_out if isinstance(maybe_out, CollectorOutput) else None
    if out is None:
        return {}
    specs: dict[str, FixtureSpec] = {}
    fixture_nodes: list[cst.FunctionDef] = []
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

    # helper: infer filename literals from local_assignments recorded by collector
    def _infer_filename_for_local(local_name: str, cls_obj: Any) -> Optional[str]:
        try:
            local_map = getattr(cls_obj, "local_assignments", {}) or {}
            if local_name not in local_map:
                return None
            # local_map is known to contain the key here; use indexing to
            # avoid Optional return type from dict.get which confuses mypy
            assigned_call, _ = local_map[local_name]
            if not isinstance(assigned_call, cst.Call):
                return None
            # check positional first arg that is a simple string literal
            if assigned_call.args:
                for a in assigned_call.args:
                    if isinstance(getattr(a, "value", None), cst.SimpleString):
                        # strip quotes
                        s = getattr(a.value, "value", "")
                        if len(s) >= 2 and (s[0] == s[-1] == '"' or s[0] == s[-1] == "'"):
                            return s[1:-1]
            return None
        except Exception:
            return None

    def _collect_self_attrs(expr: Any) -> set[str]:
        return set(collect_self_attrs(expr))

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
                        # assignment (sometimes wrapped in an Expr node)
                        if isinstance(expr, cst.Assign):
                            for t in expr.targets:
                                target = getattr(t, "target", t)
                                if _references_attribute(target, attr):
                                    return True
                            if _references_attribute(expr.value, attr):
                                return True
                        # expression wrapper: some tests construct Assign wrapped
                        # in an Expr node. Handle Expr whose value is an Assign
                        # the same as a bare Assign so we don't miss simple forms
                        if isinstance(expr, cst.Expr):
                            inner = getattr(expr, "value", None)
                            if isinstance(inner, cst.Assign):
                                for t in inner.targets:
                                    target = getattr(t, "target", t)
                                    if _references_attribute(target, attr):
                                        return True
                                if _references_attribute(inner.value, attr):
                                    return True
                            else:
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
            # attempt to infer filename literals for fixtures created from
            # helper-local indirections (e.g., helper('file.sql') -> local)
            # when autocreate is enabled callers expect the literal embedded
            # in generated fixture code. We only do this for simple cases.
            try:
                autocreate = bool(context.get("autocreate", True))
            except Exception:
                autocreate = True
            if autocreate and value_expr is not None and isinstance(value_expr, cst.Call):
                for a in value_expr.args:
                    av = getattr(a, "value", None)
                    if isinstance(av, cst.Name):
                        inferred = _infer_filename_for_local(av.value, cls)
                        if inferred:
                            value_expr = cst.SimpleString(f'"{inferred}"')
                            break

            spec = FixtureSpec(
                name=fname, value_expr=value_expr, cleanup_statements=relevant_cleanup.copy(), yield_style=yield_style
            )
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
                        # Accept Assign directly
                        if isinstance(expr, cst.Assign):
                            target = expr.targets[0].target
                            # accept self.attr or cls.attr
                            if (
                                isinstance(target, cst.Attribute)
                                and isinstance(getattr(target, "value", None), cst.Name)
                                and getattr(getattr(target, "value", None), "value", None) in ("self", "cls")
                            ):
                                return True
                            # also accept bare name assignment like `value = None`
                            if isinstance(target, cst.Name) and target.value == attr:
                                return True
                        # Or Assign wrapped inside an Expr (some tests construct this shape)
                        if isinstance(expr, cst.Expr):
                            inner = getattr(expr, "value", None)
                            if isinstance(inner, cst.Assign):
                                target = inner.targets[0].target
                                if (
                                    isinstance(target, cst.Attribute)
                                    and isinstance(getattr(target, "value", None), cst.Name)
                                    and getattr(getattr(target, "value", None), "value", None) in ("self", "cls")
                                ):
                                    return True
                                if isinstance(target, cst.Name) and target.value == attr:
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
                # For container literals (dict/list/tuple/set) ensure they do not
                # reference self/cls attributes; if they do, treat them as
                # non-literals so we can emit fixtures that accept parameters.
                if (
                    not multi_assigned
                    and _is_literal(value_expr)
                    and not _collect_self_attrs(value_expr)
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
                        new_stmt = cast(Any, stmt).visit(_AttrRewriter(attr, fname))
                        body_stmts_small_small.append(new_stmt)
                    # IndentedBlock expects Sequence[BaseStatement]; widen types here
                    body = cst.IndentedBlock(body=list(cast(Sequence[cst.BaseStatement], body_stmts_small_small)))
                    func = cst.FunctionDef(
                        name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator]
                    )
                    fixture_nodes.append(func)
                else:
                    # bind to local_name and yield it; rewrite cleanup to local_name
                    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(cst.Name(local_name)))])
                    # accumulate as Any to accept Assign (BaseStatement) and
                    # SimpleStatementLine/other small-statement flavors
                    body_stmts_small_small = [assign, yield_stmt]
                    for stmt in spec.cleanup_statements:
                        new_stmt = cast(Any, stmt).visit(_AttrRewriter(attr, local_name))
                        body_stmts_small_small.append(new_stmt)
                    body = cst.IndentedBlock(body=list(cast(Sequence[cst.BaseStatement], body_stmts_small_small)))
                    func = cst.FunctionDef(
                        name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator]
                    )
                    fixture_nodes.append(func)
            else:
                # For simple literal values, return the literal directly instead
                # of binding to a local name, preserving the original intent
                # (e.g., return 42). For non-literals we still bind to a local
                # name and return it to keep cleanup rewriting consistent.
                # Only treat a literal as literal-return if it does not
                # reference self/cls attributes; otherwise emit a
                # parameterized fixture returning the rewritten expression.
                if _is_literal(value_expr) and not _collect_self_attrs(value_expr):
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(cast(cst.BaseExpression, value_expr))])
                    body = cst.IndentedBlock(body=[return_stmt])
                    func = cst.FunctionDef(
                        name=cst.Name(fname), params=cst.Parameters(), body=body, decorators=[decorator]
                    )
                    fixture_nodes.append(func)
                else:
                    # Non-literal: produce a fixture that accepts parameters for
                    # any referenced self/cls attributes and returns the expression
                    # directly. This matches expected golden output like
                    # def config_dir(temp_dir):
                    #     return Path(temp_dir) / "config"
                    refs = _collect_self_attrs(value_expr)
                    # Build Parameter list from refs in deterministic order
                    param_names = [r for r in sorted(refs)]
                    params = cst.Parameters(params=[cst.Param(name=cst.Name(n)) for n in param_names])

                    # Replace occurrences of self.attr with bare param Name
                    class _ReplaceSelfWithParam(cst.CSTTransformer):
                        def __init__(self, refs_set: set[str]) -> None:
                            self.refs = refs_set

                        def leave_Attribute(
                            self, original: cst.Attribute, updated: cst.Attribute
                        ) -> cst.BaseExpression:
                            if isinstance(original.value, cst.Name) and original.value.value in ("self", "cls"):
                                if isinstance(original.attr, cst.Name) and original.attr.value in self.refs:
                                    return cst.Name(original.attr.value)
                            return updated

                    # value_expr may be None according to CollectorOutput
                    # typing; defensively handle that case by returning a
                    # literal None expression so mypy and runtime are safe.
                    if value_expr is None:
                        rewritten = cst.Name("None")
                    else:
                        rewritten = value_expr.visit(_ReplaceSelfWithParam(refs))
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(cast(cst.BaseExpression, rewritten))])
                    body = cst.IndentedBlock(body=[return_stmt])
                    func = cst.FunctionDef(name=cst.Name(fname), params=params, body=body, decorators=[decorator])
                    fixture_nodes.append(func)
            # detect if any cleanup statements reference shutil so we can
            # request an import from the import_injector stage.
            for stmt in spec.cleanup_statements:
                try:
                    rendered = cst.Module(body=[stmt]).code
                    if "shutil." in rendered or "import shutil" in rendered:
                        # attach a flag to the result via context-like variable
                        # we'll include this in final result below
                        spec._needs_shutil = True  # type: ignore[attr-defined]
                except Exception:
                    pass
            # attempt to infer filename literals for fixtures created from
            # helper-local indirections (e.g., helper('file.sql') -> local)
            # when autocreate is enabled callers expect the literal embedded
            # in generated fixture code. We only do this for simple cases.
            try:
                autocreate = bool(context.get("autocreate", True))
            except Exception:
                autocreate = True
            if autocreate and value_expr is not None:
                # value_expr may be a call wrapping a local (e.g., str(local))
                if isinstance(value_expr, cst.Call):
                    for a in value_expr.args:
                        av = getattr(a, "value", None)
                        if isinstance(av, cst.Name):
                            inferred = _infer_filename_for_local(av.value, cls)
                            if inferred:
                                # replace the value expression with the literal
                                value_expr = cst.SimpleString(f'"{inferred}"')
                                spec.value_expr = value_expr
                                break
    # After building per-attribute fixture nodes, try to bundle nearby
    # local assignments into NamedTuples and emit paired fixtures. This
    # logic is extracted into generator_parts.namedtuple_bundler so we
    # can unit-test it independently and avoid moving code that relies
    # on lexical locals into a new module.
    try:
        prepend_nodes, bundler_typing = bundle_named_locals(out.classes, module_level_names)
    except Exception:
        prepend_nodes, bundler_typing = [], set()

    # Collect typing names required by scanned value expressions. Simple
    # heuristics: list/tuple/dict/set -> List/Tuple/Dict/Set, and any
    # yield-style fixture requires Generator.
    typing_needed: set[str] = set(bundler_typing)
    any_yield = False

    def _type_name_for_literal(node: cst.BaseExpression) -> tuple[cst.BaseExpression | None, set[str]]:
        """Return a libcst node representing a typing annotation and a set of typing names.

        The returned node can be used inside cst.Annotation(annotation=...).
        """
        names: set[str] = set()
        if isinstance(node, cst.List):
            names.add("List")
            # infer simple element type when possible
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
            # try to infer element type
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
            # infer key/value types simply from first pair
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
        # fallback: no specific typing
        return None, set()

    for spec in specs.values():
        v = spec.value_expr
        if isinstance(v, cst.List):
            typing_needed.add("List")
        elif isinstance(v, cst.Tuple):
            typing_needed.add("Tuple")
        elif isinstance(v, cst.Set):
            typing_needed.add("Set")
        elif isinstance(v, cst.Dict):
            typing_needed.add("Dict")
        else:
            # conservative fallback: if expression is a comprehension or
            # otherwise complex, include Any so callers can fall back.
            if v is not None and not _is_literal(v):
                typing_needed.add("Any")
        if spec.yield_style:
            any_yield = True

    if any_yield:
        typing_needed.add("Generator")

    # Prepend any NamedTuple/fixture nodes produced by the bundler so they
    # appear before per-attribute fixtures in the generated module.
    # Attach return annotations to generated fixture functions when we
    # can infer a precise typing annotation for the fixture value.
    # To preserve certain golden outputs that expect parameterized fixtures
    # to remain un-annotated, only attach annotations for fixtures that
    # accept no parameters (params list empty).
    annotated_nodes: list[cst.BaseStatement] = []
    for n in fixture_nodes:
        if isinstance(n, cst.FunctionDef):
            # find corresponding spec by name
            nm = n.name.value
            spec_opt: Optional[FixtureSpec] = specs.get(nm)
            if spec_opt is not None and spec_opt.value_expr is not None:
                # only annotate if the fixture has no parameters
                if not n.params.params:
                    ann_node, extra_names = _type_name_for_literal(spec_opt.value_expr)
                    if ann_node is not None:
                        annotated = n.with_changes(returns=cst.Annotation(annotation=ann_node))
                        annotated_nodes.append(annotated)
                        typing_needed.update(extra_names)
                        continue
        annotated_nodes.append(n)

    final_nodes = list(prepend_nodes) + annotated_nodes

    result: dict[str, object] = {"fixture_specs": specs, "fixture_nodes": final_nodes}
    if typing_needed:
        # return as a sorted list for determinism
        result["needs_typing_names"] = sorted(typing_needed)
    # propagate shutil import requirement if any spec flagged it
    needs_shutil = any(getattr(s, "_needs_shutil", False) for s in specs.values())
    if needs_shutil:
        result["needs_shutil_import"] = True
    return result


# Backwards-compatible alias used by the pipeline and older callers
generator = generator_stage
