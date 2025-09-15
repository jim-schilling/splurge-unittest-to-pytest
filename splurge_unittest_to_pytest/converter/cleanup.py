"""Cleanup analysis helpers extracted from the main transformer.

These are pure functions that inspect libcst statement/expression nodes to
determine whether cleanup statements reference a given attribute name.
"""

from typing import Any

import libcst as cst

from .cleanup_checks import references_attribute
from .cleanup_inspect import simple_stmt_references_attribute

DOMAINS = ["converter", "teardown"]

# Associated domains for this module


def extract_relevant_cleanup(cleanup_statements: list[Any], attr_name: str) -> list[Any]:
    """Return a list of cleanup statements that reference the given attribute.

    The implementation scans common statement shapes (Expr with Call, Assign,
    If blocks, IndentedBlock) and returns statements that reference attr_name.
    """
    relevant_statements: list[Any] = []

    def inspect_stmt(s: cst.BaseStatement) -> None:
        # Simple statement lines are delegated to a focused helper for clarity / testability
        if isinstance(s, cst.SimpleStatementLine):
            if simple_stmt_references_attribute(s, attr_name):
                relevant_statements.append(s)
                return

        # If statements: test/body/orelse
        if isinstance(s, cst.If):
            # Prefer AST-aware detection
            if references_attribute(s.test, attr_name):
                relevant_statements.append(s)
                return
            # Fallback: some comparison targets can be wrapped in library-specific
            # nodes; fall back to textual scan of the test expression as a last resort.
            test_code = getattr(s.test, "code", None)
            if isinstance(test_code, str) and attr_name in test_code:
                relevant_statements.append(s)
                return
            for inner in getattr(s.body, "body", []):
                inspect_stmt(inner)
                if relevant_statements and relevant_statements[-1] is inner:
                    # Found a matching inner statement; record the enclosing If
                    # rather than the inner statement to preserve context.
                    relevant_statements.pop()
                    relevant_statements.append(s)
                    return
            orelse = getattr(s, "orelse", None)
            if orelse:
                if isinstance(orelse, cst.IndentedBlock):
                    for inner in getattr(orelse, "body", []):
                        inspect_stmt(inner)
                        if relevant_statements and relevant_statements[-1] is inner:
                            relevant_statements.pop()
                            relevant_statements.append(s)
                            return
                elif isinstance(orelse, cst.If):
                    inspect_stmt(orelse)
                    if relevant_statements and relevant_statements[-1] is orelse:
                        # If the nested If contained the match, replace it with the outer If
                        relevant_statements.pop()
                        relevant_statements.append(s)
                        return

        # IndentedBlock: inspect contained statements
        if isinstance(s, cst.IndentedBlock):
            for inner in getattr(s, "body", []):
                inspect_stmt(inner)
                if relevant_statements and relevant_statements[-1] is inner:
                    return

    for stmt in cleanup_statements:
        inspect_stmt(stmt)

    return relevant_statements
