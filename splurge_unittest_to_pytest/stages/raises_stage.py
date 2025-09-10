"""Raises stage: handle various forms of assertRaises/assertRaisesRegex.

This stage focuses on converting both context-manager uses and callable-form
uses of assertRaises/assertRaisesRegex into pytest.raises equivalents.
"""
from __future__ import annotations

from typing import Sequence

import libcst as cst


class RaisesRewriter(cst.CSTTransformer):
    """Rewrites assertRaises forms to pytest.raises.

    - with self.assertRaises(E): ...  -> with pytest.raises(E): ...
    - with self.assertRaisesRegex(E, 'pat'): -> with pytest.raises(E, match='pat'):
    - self.assertRaises(E, func, *args) -> with pytest.raises(E): func(*args)
    - self.assertRaisesRegex(E, 'pat', func, *args) -> with pytest.raises(E, match='pat'): func(*args)
    """

    def __init__(self) -> None:
        super().__init__()
        # set when we create/replace nodes that introduce pytest usage
        self.made_changes: bool = False


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
        new_first = first.with_changes(item=new_item)
        new_items = [new_first] + list(updated_node.items[1:])
        self.made_changes = True
        return updated_node.with_changes(items=new_items)

    def leave_Expr(self, original_node: cst.Expr, updated_node: cst.Expr):
        # handle functional form: self.assertRaises(E, func, *args)
        if isinstance(updated_node.value, cst.Call):
            call = updated_node.value
            info = self._is_assert_raises_call(call)
            if info is None:
                return updated_node
            method_name = info
            args = call.args
            # functional form requires at least 2 args: exception, callable
            if len(args) >= 2:
                exc_arg = args[0]
                func_call = cst.Call(func=args[1].value, args=list(args[2:]))
                # wrap the function call in a with pytest.raises(...): block
                # For assertRaisesRegex the pattern is the second arg, so pass exc_arg and pattern as needed
                if method_name == 'assertRaises':
                    with_item = self._create_pytest_raises_item(method_name, [exc_arg])
                else:
                    # assume args like (Exc, pattern, func, ...)
                    with_item = self._create_pytest_raises_item(method_name, [exc_arg, args[1]])
                # craft a With node
                new_with = cst.With(items=[with_item], body=cst.IndentedBlock(body=[cst.SimpleStatementLine([cst.Expr(func_call)])]))
                self.made_changes = True
                return new_with
        return updated_node

    # helpers
    def _is_assert_raises_call(self, call_node: cst.Call) -> str | None:
        # check for self.assertRaises or self.assertRaisesRegex
        try:
            if isinstance(call_node.func, cst.Attribute):
                if isinstance(call_node.func.value, cst.Name) and call_node.func.value.value == 'self':
                    name = call_node.func.attr.value
                    if name in ('assertRaises', 'assertRaisesRegex'):
                        return name
        except Exception:
            pass
        return None

    def _create_pytest_raises_item(self, method_name: str, args: Sequence[cst.Arg]) -> cst.WithItem:
        # Build pytest.raises(...) call; for Regex variant, bind second arg as match=
        # mark that pytest import will be needed by the pipeline
        try:
            # creation of a pytest.raises call implies we'll need pytest imported
            self.made_changes = True
        except Exception:
            # defensive: if something goes wrong, don't raise from transformer
            pass
        if method_name == 'assertRaises':
            return cst.WithItem(item=cst.Call(func=cst.Attribute(value=cst.Name('pytest'), attr=cst.Name('raises')), args=list(args)))
        # assertRaisesRegex: expect args like (Exc, pattern, ...)
        if len(args) >= 2:
            exc = args[0]
            pat = args[1]
            return cst.WithItem(item=cst.Call(func=cst.Attribute(value=cst.Name('pytest'), attr=cst.Name('raises')), args=[exc, cst.Arg(keyword=cst.Name('match'), value=pat.value)]))
        # fallback
        return cst.WithItem(item=cst.Call(func=cst.Attribute(value=cst.Name('pytest'), attr=cst.Name('raises')), args=list(args)))


def raises_stage(context: dict) -> dict:
    module: cst.Module = context.get('module')
    if module is None:
        return {}
    transformer = RaisesRewriter()
    new_mod = module.visit(transformer)
    # signal the import injector only if we actually created pytest.raises usage
    return {'module': new_mod, 'needs_pytest_import': bool(getattr(transformer, 'made_changes', False))}
