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
from splurge_unittest_to_pytest.stages.generator_parts.filename_inferer import infer_filename_for_local
from splurge_unittest_to_pytest.stages.generator_parts.references_attr import references_attribute
from splurge_unittest_to_pytest.stages.generator_parts.cleanup_checks import is_simple_cleanup_statement
from splurge_unittest_to_pytest.stages.generator_parts.name_allocator import choose_local_name
from splurge_unittest_to_pytest.stages.generator_parts.attr_rewriter import AttrRewriter
from splurge_unittest_to_pytest.stages.generator_parts.replace_self_param import ReplaceSelfWithParam
from splurge_unittest_to_pytest.stages.collector import CollectorOutput
from splurge_unittest_to_pytest.stages.generator_parts.generator_core import GeneratorCore
from splurge_unittest_to_pytest.stages.generator_parts.shutil_detector import cleanup_needs_shutil


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
        # thin wrapper delegating to extracted helper
        return references_attribute(expr, attr_name)

    # snapshot module-level names to detect collisions that should force
    # binding to a local name even when the value is a literal.
    module_level_names = set(used_local_names)

    # helper: infer filename literals from local_assignments recorded by collector
    def _infer_filename_for_local(local_name: str, cls_obj: Any) -> Optional[str]:
        # thin wrapper to call the extracted helper; keeps local call sites
        return infer_filename_for_local(local_name, cls_obj)

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
                # thin wrapper to keep local call sites unchanged while
                # delegating the deterministic naming logic to a testable
                # helper module.
                return choose_local_name(base, taken)

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
            def _AttrRewriter(target: str, local: str) -> cst.CSTTransformer:
                # thin wrapper returning a transformer instance for local
                # call sites that previously constructed the inline class.
                return AttrRewriter(target, local)

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
                    # delegate to extracted helper
                    return is_simple_cleanup_statement(s, attr)

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


                    # value_expr may be None according to CollectorOutput
                    # typing; defensively handle that case by returning a
                    # literal None expression so mypy and runtime are safe.
                    if value_expr is None:
                        rewritten = cst.Name("None")
                    else:
                        rewritten = value_expr.visit(ReplaceSelfWithParam(refs))
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(cast(cst.BaseExpression, rewritten))])
                    body = cst.IndentedBlock(body=[return_stmt])
                    func = cst.FunctionDef(name=cst.Name(fname), params=params, body=body, decorators=[decorator])
                    fixture_nodes.append(func)
            # detect if any cleanup statements reference shutil so we can
            # request an import from the import_injector stage.
            if cleanup_needs_shutil(spec.cleanup_statements):
                spec._needs_shutil = True  # type: ignore[attr-defined]
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

    # Delegate final annotation/typing and result assembly to GeneratorCore
    core = GeneratorCore()
    return core.finalize(prepend_nodes, fixture_nodes, specs, bundler_typing)


# Backwards-compatible alias used by the pipeline and older callers
generator = generator_stage
