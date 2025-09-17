"""Convert unittest.assertRaises forms to pytest.raises and fix attributes.

Converts both context-manager and callable ``assertRaises`` usages to
``pytest.raises`` and updates bound exception attribute access to use
``ExceptionInfo.value``.

Publics:
    ExceptionAttrRewriter
    RaisesRewriter

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Sequence, Optional, Any, cast

import libcst as cst

DOMAINS = ["stages", "exceptions"]

# Associated domains for this module


class ExceptionAttrRewriter(cst.CSTTransformer):
    """Rewrite ``NAME.exception`` to ``NAME.value`` for a target name.

    After converting ``assertRaises`` context managers to ``pytest.raises``
    the bound exception object is an ``ExceptionInfo`` whose attribute is
    ``value`` rather than ``exception``. This transformer updates attribute
    accesses accordingly while respecting lexical shadowing.
    """

    def __init__(self, target_name: str) -> None:
        super().__init__()
        self._target = target_name
        # lexical scope stack for shadowing checks
        self._scope_stack: list[set[str]] = [set()]

    def _add_bound_name(self, name: str) -> None:
        try:
            if self._scope_stack:
                self._scope_stack[-1].add(name)
        except Exception:
            pass

    def _is_name_bound_in_current_scope(self, name: str) -> bool:
        try:
            if not self._scope_stack:
                return False
            return name in self._scope_stack[-1]
        except Exception:
            return False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Any:
        self._scope_stack.append(set())
        try:
            params = node.params
            for p in params.params:
                if isinstance(p.name, cst.Name):
                    self._add_bound_name(p.name.value)
            for p in params.posonly_params:
                if isinstance(p.name, cst.Name):
                    self._add_bound_name(p.name.value)
            for p in params.kwonly_params:
                if isinstance(p.name, cst.Name):
                    self._add_bound_name(p.name.value)
        except Exception:
            pass
        return node

    def leave_FunctionDef(self, original: cst.FunctionDef, updated: cst.FunctionDef) -> cst.FunctionDef:
        try:
            if self._scope_stack:
                self._scope_stack.pop()
        except Exception:
            pass
        return updated

    def visit_Lambda(self, node: cst.Lambda) -> Any:
        self._scope_stack.append(set())
        try:
            params = node.params
            for p in params.params:
                if isinstance(p.name, cst.Name):
                    self._add_bound_name(p.name.value)
        except Exception:
            pass
        return node

    def leave_Lambda(self, original: cst.Lambda, updated: cst.Lambda) -> cst.Lambda:
        try:
            if self._scope_stack:
                self._scope_stack.pop()
        except Exception:
            pass
        return updated

    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.Attribute:
        try:
            if isinstance(updated.value, cst.Name) and updated.value.value == self._target:
                # do not rewrite if the name is shadowed in the current scope
                if self._is_name_bound_in_current_scope(self._target):
                    return updated
                if isinstance(updated.attr, cst.Name) and updated.attr.value == "exception":
                    return updated.with_changes(attr=cst.Name("value"))
        except Exception:
            pass
        return updated


class RaisesRewriter(cst.CSTTransformer):
    """Rewrite ``assertRaises`` usages into ``pytest.raises`` equivalents.

    Supported rewrites include:

    - ``with self.assertRaises(E): ...`` -> ``with pytest.raises(E): ...``
    - ``with self.assertRaisesRegex(E, 'pat')`` -> ``with pytest.raises(E, match='pat')``
    - ``self.assertRaises(E, func, *args)`` -> ``with pytest.raises(E): func(*args)``
    - Callable forms with regex -> ``pytest.raises(..., match=...)``
    """

    def __init__(self) -> None:
        super().__init__()
        # set when we create/replace nodes that introduce pytest usage
        self.made_changes: bool = False
        # names bound by `with ... as NAME` that should have exception->value rewrites
        self._exception_var_names: set[str] = set()
        # lexical scope stack: each entry is a set of names bound in that scope
        # the top of the stack represents the currently visited innermost scope
        # module-level scope is the first entry
        self._scope_stack: list[set[str]] = [set()]

    def enter_With(self, original_node: cst.With) -> None:
        # Record `as NAME` for assertRaises context managers early so child
        # nodes (nested functions, comprehensions, lambdas) see the name set
        # during traversal and can be rewritten accordingly.
        try:
            if not original_node.items:
                return None
            first = original_node.items[0]
            if not isinstance(first.item, cst.Call):
                return None
            method = self._is_assert_raises_call(first.item)
            if method is None:
                return None
            asname = first.asname
            if asname and isinstance(asname.name, cst.Name):
                self._exception_var_names.add(asname.name.value)
        except Exception:
            # be defensive: do not fail traversal on unexpected node shapes
            return None

    def leave_With(self, original_node: cst.With, updated_node: cst.With) -> cst.With:
        # handle with self.assertRaises(...) as cm: or without 'as'
        if not updated_node.items:
            return updated_node
        first = updated_node.items[0]
        # item must be a Call
        if not isinstance(first.item, cst.Call):
            return updated_node
        method = self._is_assert_raises_call(first.item)
        if method is None:
            return updated_node
        new_item = self._create_pytest_raises_item(method, first.item.args)
        # _create_pytest_raises_item may return a WithItem (used when
        # constructing new With nodes) or a bare Call. When updating the
        # existing WithItem we must preserve the original `asname` field.
        # Ensure we assign the Call expression to `first.item` while
        # leaving `first.asname` intact.
        try:
            if isinstance(new_item, cst.WithItem):
                call_expr: cst.BaseExpression = new_item.item
            else:
                # new_item should be a BaseExpression in this branch
                call_expr = cast(cst.BaseExpression, new_item)
        except Exception:
            # As a last resort, fall back to the original first.item
            call_expr = first.item
        new_first = first.with_changes(item=call_expr)
        new_items = [new_first] + list(updated_node.items[1:])
        self.made_changes = True

        # If the original with used an `as NAME` context manager (e.g. `as cm`),
        # record the name so attribute accesses elsewhere (after the with) can be
        # updated from NAME.exception -> NAME.value to match pytest.ExceptionInfo.
        asname_name: str | None = None
        try:
            asname = first.asname
            if asname and isinstance(asname.name, cst.Name):
                asname_name = asname.name.value
        except Exception:
            asname_name = None

        if asname_name:
            self._exception_var_names.add(asname_name)

        return updated_node.with_changes(items=new_items)

    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.Attribute:
        # Globally rewrite NAME.exception -> NAME.value for any NAME recorded
        try:
            if isinstance(updated.value, cst.Name):
                name = updated.value.value
                # only rewrite if this name was recorded and is NOT shadowed by a binding
                if name in self._exception_var_names and not self._is_name_bound_in_current_scope(name):
                    if isinstance(updated.attr, cst.Name) and updated.attr.value == "exception":
                        return updated.with_changes(attr=cst.Name("value"))
        except Exception:
            pass
        return updated

    # Scope tracking helpers -------------------------------------------------
    def _add_bound_name(self, name: str) -> None:
        try:
            if self._scope_stack:
                self._scope_stack[-1].add(name)
        except Exception:
            pass

    def _is_name_bound_in_current_scope(self, name: str) -> bool:
        try:
            # check innermost scope first
            if not self._scope_stack:
                return False
            return name in self._scope_stack[-1]
        except Exception:
            return False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Any:
        # entering a new function creates a new lexical scope
        self._scope_stack.append(set())
        # add parameters to the scope so they shadow outer names
        try:
            params = node.params
            for p in params.params:
                if isinstance(p.name, cst.Name):
                    self._add_bound_name(p.name.value)
            for p in params.posonly_params:
                if isinstance(p.name, cst.Name):
                    self._add_bound_name(p.name.value)
            for p in params.kwonly_params:
                if isinstance(p.name, cst.Name):
                    self._add_bound_name(p.name.value)
        except Exception:
            pass
        return node

    def leave_FunctionDef(self, original: cst.FunctionDef, updated: cst.FunctionDef) -> cst.FunctionDef:
        # leaving a function pops the lexical scope
        try:
            if self._scope_stack:
                self._scope_stack.pop()
        except Exception:
            pass
        return updated

    def visit_Lambda(self, node: cst.Lambda) -> Any:
        # lambda introduces a new scope with parameters bound
        self._scope_stack.append(set())
        try:
            params = node.params
            for p in params.params:
                if isinstance(p.name, cst.Name):
                    self._add_bound_name(p.name.value)
        except Exception:
            pass
        return node

    def leave_Lambda(self, original: cst.Lambda, updated: cst.Lambda) -> cst.Lambda:
        try:
            if self._scope_stack:
                self._scope_stack.pop()
        except Exception:
            pass
        return updated

    def visit_ListComp(self, node: cst.ListComp) -> Any:
        # comprehensions have their own implicit scope for target names
        self._scope_stack.append(set())
        try:
            # LibCST versions differ in how comprehension nodes expose
            # their generator list; be defensive and use getattr to avoid
            # mypy/typed-visitor issues across versions.
            gens = getattr(node, "for_in", None)
            if gens is None:
                gens_iter = getattr(node, "generators", []) or []
            else:
                gens_iter = getattr(gens, "generators", []) or []
            for gen in gens_iter:
                target = getattr(gen, "target", None)
                # if the target is a Name, bind it
                if isinstance(target, cst.Name):
                    self._add_bound_name(target.value)
        except Exception:
            pass
        return node

    def leave_ListComp(self, original: cst.ListComp, updated: cst.ListComp) -> cst.ListComp:
        try:
            if self._scope_stack:
                self._scope_stack.pop()
        except Exception:
            pass
        return updated

    # Use Any return to accommodate libcst typed-visitor signature differences
    # across versions while keeping runtime behavior unchanged.
    def leave_Expr(self, original_node: cst.Expr, updated_node: cst.Expr) -> Any:
        # non-functional expressions: nothing to do here
        return updated_node

    def leave_SimpleStatementLine(self, original: cst.SimpleStatementLine, updated: cst.SimpleStatementLine) -> Any:
        # handle functional form: self.assertRaises(E, func, *args) occurring as
        # a bare statement line. Replace the entire SimpleStatementLine with a
        # With compound statement via FlattenSentinel so codegen remains valid.
        try:
            # expect a single small-statement which is an Expr(Call(...))
            body = updated.body or []
            if len(body) != 1:
                return updated
            small = body[0]
            if not isinstance(small, cst.Expr):
                return updated
            if not isinstance(small.value, cst.Call):
                return updated
            call = small.value
            info = self._is_assert_raises_call(call)
            if info is None:
                return updated
            method_name = info
            args = call.args
            if len(args) >= 2:
                exc_arg = args[0]
                func_call = cst.Call(func=args[1].value, args=list(args[2:]))
                if method_name == "assertRaises":
                    wi = self._create_pytest_raises_item(method_name, [exc_arg])
                else:
                    wi = self._create_pytest_raises_item(method_name, [exc_arg, args[1]])
                # Ensure we have a WithItem for the With.items list
                if isinstance(wi, cst.WithItem):
                    items_list: list[cst.WithItem] = [wi]
                else:
                    items_list = [cst.WithItem(item=cast(cst.BaseExpression, wi))]
                new_with = cst.With(
                    items=items_list,
                    body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(func_call)])]),
                )
                self.made_changes = True
                return cast(Any, cst.FlattenSentinel([new_with]))
        except Exception:
            pass
        return updated

    # helpers
    def _is_assert_raises_call(self, call_node: cst.Call) -> str | None:
        # check for self.assertRaises or self.assertRaisesRegex
        try:
            if isinstance(call_node.func, cst.Attribute):
                if isinstance(call_node.func.value, cst.Name) and call_node.func.value.value == "self":
                    name = call_node.func.attr.value
                    if name in ("assertRaises", "assertRaisesRegex"):
                        return name
        except Exception:
            pass
        return None

    def _create_pytest_raises_item(
        self, method_name: str, args: Sequence[cst.Arg]
    ) -> cst.WithItem | cst.BaseExpression:
        # Build pytest.raises(...) call; for Regex variant, bind second arg as match=
        # mark that pytest import will be needed by the pipeline
        try:
            # creation of a pytest.raises call implies we'll need pytest imported
            self.made_changes = True
        except Exception:
            # defensive: if something goes wrong, don't raise from transformer
            pass
        if method_name == "assertRaises":
            return cst.WithItem(
                item=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")), args=list(args))
            )
        # assertRaisesRegex: expect args like (Exc, pattern, ...)
        if len(args) >= 2:
            exc = args[0]
            pat = args[1]
            return cst.WithItem(
                item=cst.Call(
                    func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")),
                    args=[exc, cst.Arg(keyword=cst.Name("match"), value=pat.value)],
                )
            )
        # fallback
        return cst.WithItem(
            item=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")), args=list(args))
        )


def raises_stage(context: dict[str, object]) -> dict[str, object]:
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is None:
        return {}
    transformer = RaisesRewriter()
    new_mod = module.visit(transformer)
    # After rewriting unittest assertRaises -> pytest.raises we may still have
    # attribute accesses like `cm.exception` that need to become `cm.value`.
    # Collect any names bound by `with pytest.raises(...) as NAME` in the
    # transformed module (these may have been introduced by this stage or
    # pre-existed). Then run a targeted ExceptionAttrRewriter pass for each
    # name to ensure NAME.exception -> NAME.value is applied everywhere.
    try:
        pytest_asnames: set[str] = set()
        for node in new_mod.body:
            # look for top-level With nodes; do a defensive traversal for nested ones
            if isinstance(node, cst.With):
                items = node.items or []
                if not items:
                    continue
                first = items[0]
                # item must be a Call to pytest.raises
                call = first.item
                if isinstance(call, cst.Call) and isinstance(call.func, cst.Attribute):
                    func = call.func
                    if (
                        isinstance(func.value, cst.Name)
                        and func.value.value == "pytest"
                        and isinstance(func.attr, cst.Name)
                        and func.attr.value == "raises"
                    ):
                        asname = first.asname
                        if asname and isinstance(asname.name, cst.Name):
                            pytest_asnames.add(asname.name.value)
        # also include any names collected during the rewrite pass
        pytest_asnames.update(getattr(transformer, "_exception_var_names", set()))
        # apply ExceptionAttrRewriter for each collected name
        for name in sorted(pytest_asnames):
            if name:
                new_mod = new_mod.visit(ExceptionAttrRewriter(name))
    except Exception:
        # be defensive: don't fail the entire stage on unexpected shapes
        pass

    # signal the import injector only if we actually created pytest.raises usage
    return {"module": new_mod, "needs_pytest_import": bool(getattr(transformer, "made_changes", False))}


def exceptioninfo_normalizer_stage(context: dict[str, object]) -> dict[str, object]:
    """Pipeline stage: ensure NAME.exception -> NAME.value for pytest.raises bindings.

    This runs after other stages (e.g., generator) that may restructure code and
    re-introduce attribute accesses that need normalizing. It scans the entire
    module for `with pytest.raises(...) as NAME` bindings and applies a
    targeted ExceptionAttrRewriter pass for each found name.
    """
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is None:
        return {}

    class _WithCollector(cst.CSTVisitor):
        def __init__(self) -> None:
            self.names: set[str] = set()

        def visit_With(self, node: cst.With) -> None:
            try:
                items = node.items or []
                if not items:
                    return None
                first = items[0]
                call = first.item
                if isinstance(call, cst.Call) and isinstance(call.func, cst.Attribute):
                    func = call.func
                    if (
                        isinstance(func.value, cst.Name)
                        and func.value.value == "pytest"
                        and isinstance(func.attr, cst.Name)
                        and func.attr.value == "raises"
                    ):
                        asname = first.asname
                        if asname and isinstance(asname.name, cst.Name):
                            self.names.add(asname.name.value)
            except Exception:
                pass

    collector = _WithCollector()
    module.visit(collector)

    new_mod = module
    try:
        for name in sorted(collector.names):
            if name:
                new_mod = new_mod.visit(ExceptionAttrRewriter(name))
    except Exception:
        # defensive: do not fail the pipeline on unexpected shapes
        return {"module": module}

    return {"module": new_mod}
