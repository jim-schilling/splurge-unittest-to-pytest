from __future__ import annotations

import libcst as cst
from libcst.metadata import PositionProvider


class ReplacementRegistry:
    """Record planned replacements keyed by node source position.

    Recordings are keyed by a 4-tuple (start_line, start_col, end_line, end_col)
    derived from PositionProvider metadata. This allows matching nodes across
    transformer passes even if object identity changes.
    """

    def __init__(self) -> None:
        # map from position tuple to replacement node
        self.replacements: dict[tuple[int, int, int, int], cst.CSTNode] = {}

    @staticmethod
    def key_from_position(pos) -> tuple[int, int, int, int]:
        return (pos.start.line, pos.start.column, pos.end.line, pos.end.column)

    def record(self, pos, new_node: cst.CSTNode) -> None:
        key = self.key_from_position(pos)
        self.replacements[key] = new_node

    def get(self, pos) -> cst.CSTNode | None:
        return self.replacements.get(self.key_from_position(pos))


class ReplacementApplier(cst.CSTTransformer):
    """Second-pass transformer that applies replacements recorded in a
    ReplacementRegistry. Depends on PositionProvider metadata being available.
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, registry: ReplacementRegistry) -> None:
        super().__init__()
        self.registry = registry

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        # If an expression-level replacement exists for this call, apply it.
        try:
            pos = self.get_metadata(PositionProvider, original_node)
            repl = self.registry.get(pos)
            if repl is not None and isinstance(repl, cst.BaseExpression):
                return repl  # replace the call expression
        except Exception:
            pass
        return updated_node

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.BaseStatement:
        # If the simple statement is a single Expr(Call(...)) and the recorded
        # replacement for that Call is a statement (e.g., Assert), substitute it.
        try:
            if len(original_node.body) == 1 and isinstance(original_node.body[0], cst.Expr):
                expr = original_node.body[0].value
                if isinstance(expr, cst.Call):
                    pos = self.get_metadata(PositionProvider, expr)
                    repl = self.registry.get(pos)
                    if repl is not None and isinstance(repl, cst.BaseStatement):
                        return repl
        except Exception:
            pass
        return updated_node
