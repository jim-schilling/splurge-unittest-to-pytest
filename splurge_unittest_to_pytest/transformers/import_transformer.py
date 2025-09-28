"""Import-related CST helpers extracted from unittest_transformer.

These helpers manage insertion of pytest/re imports and removal of unused
unittest imports. They are written to accept an optional transformer object
when they need to consult transformer state (e.g., needs_re_import, re_alias,
re_search_name).
"""

from __future__ import annotations

import libcst as cst


def add_pytest_imports(code: str, transformer: object | None = None) -> str:
    """Ensure `import pytest` and `import re` are present when needed.

    If `transformer` is provided, the function will consult attributes on it
    (needs_re_import, re_alias, re_search_name) to decide whether to add an
    `import re` line. The function performs a quick string-level guard to
    avoid duplicate insertion and uses libcst nodes to construct imports.
    """
    try:
        # Quick string-level guard: if pytest is already imported in source text,
        # skip AST insertion to avoid duplicates.
        if "import pytest" in code or "from pytest" in code:
            return code

        module = cst.parse_module(code)

        # Helper: detect dynamic imports like __import__('pytest') or importlib.import_module('pytest')
        class _DynImportFinder(cst.CSTVisitor):
            def __init__(self, name: str) -> None:
                self.name = name
                self.found = False

            def visit_Call(self, node: cst.Call) -> None:
                try:
                    # __import__('name')
                    if isinstance(node.func, cst.Name) and node.func.value == "__import__":
                        if node.args and isinstance(node.args[0].value, cst.SimpleString):
                            s = node.args[0].value.value.strip("'\"")
                            if s == self.name:
                                self.found = True
                                return

                    # importlib.import_module('name') or something.import_module('name')
                    if isinstance(node.func, cst.Attribute) and isinstance(node.func.attr, cst.Name):
                        if node.func.attr.value == "import_module":
                            if node.args and isinstance(node.args[0].value, cst.SimpleString):
                                s = node.args[0].value.value.strip("'\"")
                                if s == self.name:
                                    self.found = True
                                    return
                except Exception:
                    # Be conservative and ignore errors in detection
                    pass

        # Collect existing top-level imports. libcst may present imports either
        # as Import/ImportFrom nodes or as SimpleStatementLine wrapping an Expr
        # whose value is an Import/ImportFrom. Treat both forms equivalently.
        has_pytest = False
        has_re = False
        for node in module.body:
            imp_node: cst.CSTNode | None = None
            if isinstance(node, cst.Import | cst.ImportFrom):
                imp_node = node
            elif (
                isinstance(node, cst.SimpleStatementLine) and len(node.body) == 1 and isinstance(node.body[0], cst.Expr)
            ):
                expr_val = node.body[0].value
                if isinstance(expr_val, cst.Import | cst.ImportFrom):
                    imp_node = expr_val

            if imp_node is None:
                continue
            if isinstance(imp_node, cst.Import):
                for n in imp_node.names:
                    # n.name may be a cst.Name or a dotted cst.Attribute
                    nm = ""
                    try:
                        if isinstance(n.name, cst.Name):
                            nm = n.name.value
                        else:
                            # Reconstruct dotted name from Attribute chain
                            part: cst.BaseExpression = n.name
                            parts: list[str] = []
                            # Walk Attribute chain and collect attr/name values
                            while isinstance(part, cst.Attribute):
                                if isinstance(part.attr, cst.Name):
                                    parts.insert(0, part.attr.value)
                                # narrow type for part.value for the next iteration
                                part = part.value
                            if isinstance(part, cst.Name):
                                parts.insert(0, part.value)
                            nm = ".".join(parts)
                    except Exception:
                        nm = ""

                    if nm == "pytest":
                        has_pytest = True
                    if nm == "re":
                        has_re = True
            elif isinstance(imp_node, cst.ImportFrom):
                if isinstance(imp_node.module, cst.Name) and imp_node.module.value == "pytest":
                    has_pytest = True
                if isinstance(imp_node.module, cst.Name) and imp_node.module.value == "re":
                    has_re = True

        # Also treat dynamic import calls as evidence the module is present/used
        try:
            if not has_pytest:
                finder = _DynImportFinder("pytest")
                module.visit(finder)
                if finder.found:
                    has_pytest = True
            if not has_re:
                finder = _DynImportFinder("re")
                module.visit(finder)
                if finder.found:
                    has_re = True
        except Exception:
            pass

        # Build a mutable copy of the module body for insertion. We avoid
        # inserting explicit EmptyLine nodes here to keep typing simple; the
        # formatter can adjust spacing later.
        new_body = list(module.body)
        insert_at = 0
        for i, node in enumerate(new_body):
            if isinstance(node, cst.SimpleStatementLine | cst.Import | cst.ImportFrom):
                insert_at = i + 1
                continue
            break

        if not has_pytest:
            imp = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name(value="pytest"))])])
            new_body.insert(insert_at, imp)

        needs_re = False
        re_alias = None
        re_search_name = None
        if transformer is not None:
            needs_re = getattr(transformer, "needs_re_import", False)
            re_alias = getattr(transformer, "re_alias", None)
            re_search_name = getattr(transformer, "re_search_name", None)

        if needs_re and not has_re and not re_search_name:
            re_name = re_alias or "re"
            if re_name == "re":
                imp = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name(value="re"))])])
            else:
                imp = cst.SimpleStatementLine(
                    body=[
                        cst.Import(
                            names=[
                                cst.ImportAlias(
                                    name=cst.Name(value="re"), asname=cst.AsName(name=cst.Name(value=re_name))
                                )
                            ]
                        )
                    ]
                )
            new_body.insert(insert_at, imp)

        new_module = module.with_changes(body=new_body)
        return new_module.code
    except Exception:
        return code


def remove_unittest_imports_if_unused(code: str) -> str:
    """Remove top-level unittest imports when the module no longer references unittest."""
    try:
        module = cst.parse_module(code)

        # Detect whether 'unittest' is referenced elsewhere in the module
        class Finder(cst.CSTVisitor):
            def __init__(self) -> None:
                self.found = False
                self._in_import = 0
                self._depth = 0

            def visit_Import(self, node: cst.Import) -> None:
                # Entering an import statement - don't count names here
                self._in_import += 1

            def leave_Import(self, node: cst.Import) -> None:
                self._in_import -= 1

            def visit_ClassDef(self, node: cst.ClassDef) -> None:
                self._depth += 1

            def leave_ClassDef(self, node: cst.ClassDef) -> None:
                self._depth -= 1

            def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
                # Entering a from-import statement
                self._in_import += 1

            def leave_ImportFrom(self, node: cst.ImportFrom) -> None:
                self._in_import -= 1

            def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
                self._depth += 1

            def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
                self._depth -= 1

            def visit_Name(self, node: cst.Name) -> None:
                # Only mark 'unittest' as found when not inside import nodes
                if node.value == "unittest" and self._in_import == 0 and self._depth == 0:
                    self.found = True

            def visit_Call(self, node: cst.Call) -> None:
                # Treat dynamic import calls as usage of the module
                try:
                    if isinstance(node.func, cst.Name) and node.func.value == "__import__":
                        if node.args and isinstance(node.args[0].value, cst.SimpleString):
                            s = node.args[0].value.value.strip("'\"")
                            if s == "unittest":
                                self.found = True
                                return
                    if isinstance(node.func, cst.Attribute) and isinstance(node.func.attr, cst.Name):
                        if node.func.attr.value == "import_module":
                            if node.args and isinstance(node.args[0].value, cst.SimpleString):
                                s = node.args[0].value.value.strip("'\"")
                                if s == "unittest":
                                    self.found = True
                                    return
                except Exception:
                    pass

        finder = Finder()
        module.visit(finder)
        if finder.found:
            return code

        # Remove import statements that import unittest. Handle both plain Import/ImportFrom
        # nodes and SimpleStatementLine wrappers that contain Import/ImportFrom nodes.
        new_body: list[cst.CSTNode] = []
        for node in module.body:
            # If this is a SimpleStatementLine that wraps an import, normalize to the
            # inner import node for inspection, but preserve the outer node when
            # appending to new_body.
            inner: cst.CSTNode | None = None
            if isinstance(node, cst.SimpleStatementLine) and node.body:
                first = node.body[0]
                # first may be an Expr wrapping an Import or ImportFrom, or the import
                # statement itself depending on how the CST was created.
                if isinstance(first, cst.Expr) and isinstance(first.value, cst.Import | cst.ImportFrom):
                    inner = first.value
                elif isinstance(first, cst.Import | cst.ImportFrom):
                    inner = first

            # Preserve calls and other SimpleStatementLine exprs
            if inner is None:
                # Not a wrapped import - keep as-is (but skip if it's a Call? keep by default)
                new_body.append(node)
                continue

            # At this point `inner` is either Import or ImportFrom. Decide whether to keep.
            if isinstance(inner, cst.Import):
                # Keep the import if it imports names other than 'unittest'. Handle
                # dotted names properly (e.g., xml.etree.ElementTree).
                keep = False
                for n in inner.names:
                    try:
                        if isinstance(n.name, cst.Name):
                            nm = n.name.value
                        else:
                            part: cst.BaseExpression = n.name
                            parts: list[str] = []
                            while isinstance(part, cst.Attribute):
                                if isinstance(part.attr, cst.Name):
                                    parts.insert(0, part.attr.value)
                                part = part.value
                            if isinstance(part, cst.Name):
                                parts.insert(0, part.value)
                            nm = ".".join(parts)
                    except Exception:
                        nm = ""

                    if nm != "unittest":
                        keep = True
                        break
                if keep:
                    new_body.append(node)
                # else: drop the import statement entirely
                continue

            if isinstance(inner, cst.ImportFrom):
                # If this is `from unittest import ...` drop it entirely
                if isinstance(inner.module, cst.Name) and inner.module.value == "unittest":
                    continue
                # Otherwise keep
                new_body.append(node)
                continue

        new_module = module.with_changes(body=new_body)
        return new_module.code
    except Exception:
        return code
