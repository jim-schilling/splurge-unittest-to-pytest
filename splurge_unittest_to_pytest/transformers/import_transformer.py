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
                    if isinstance(n.name, cst.Name) and n.name.value == "pytest":
                        has_pytest = True
                    if isinstance(n.name, cst.Name) and n.name.value == "re":
                        has_re = True
            elif isinstance(imp_node, cst.ImportFrom):
                if isinstance(imp_node.module, cst.Name) and imp_node.module.value == "pytest":
                    has_pytest = True
                if isinstance(imp_node.module, cst.Name) and imp_node.module.value == "re":
                    has_re = True

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

            def visit_Name(self, node: cst.Name) -> None:
                if node.value == "unittest":
                    self.found = True

        finder = Finder()
        module.visit(finder)
        if finder.found:
            return code

        # Remove import statements that import unittest
        new_body: list[cst.CSTNode] = []
        for node in module.body:
            if isinstance(node, cst.SimpleStatementLine) and isinstance(node.body[0], cst.Expr):
                expr = node.body[0].value
                if isinstance(expr, cst.Call):
                    new_body.append(node)
                    continue
            if isinstance(node, cst.Import):
                keep = False
                for n in node.names:
                    if isinstance(n.name, cst.Name) and n.name.value != "unittest":
                        keep = True
                if keep:
                    new_body.append(node)
                continue
            if isinstance(node, cst.ImportFrom):
                if isinstance(node.module, cst.Name) and node.module.value == "unittest":
                    # drop this import-from
                    continue
            new_body.append(node)

        new_module = module.with_changes(body=new_body)
        return new_module.code
    except Exception:
        return code
