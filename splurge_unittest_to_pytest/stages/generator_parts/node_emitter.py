import libcst as cst
from libcst import parse_statement
from typing import List

DOMAINS = ["generator"]


# Associated domains for this module


class NodeEmitter:
    """Emit libcst AST nodes for fixtures from small body source strings.

    The emitter creates a FunctionDef node from simple lines or builds a
    composite dirs fixture when requested.
    """

    def emit_fixture_node(self, name: str, body: str, returns: str | None = None) -> cst.FunctionDef:
        # Normalize input and parse each statement with a safe fallback.
        stmts: List[cst.BaseStatement] = []
        for line in self._normalize_body(body):
            stmt = self._parse_statement_safe(line)
            # parse_statement() may return either a small or compound
            # statement; IndentedBlock accepts either, so append directly.
            stmts.append(stmt)

        body_block = cst.IndentedBlock(body=stmts)

        decorators: list[cst.Decorator] = []
        # If the body contains a yield or an explicit try:, assume it's a
        # pytest-style fixture that needs the pytest.fixture decorator.
        if any("yield" in line or "try:" in line for line in self._normalize_body(body)):
            decorators = [cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))]

        returns_node = None
        if returns:
            # simple heuristic: accept a string annotation value like 'int' or 'Tuple'
            returns_node = cst.Annotation(annotation=cst.Name(returns))

        return cst.FunctionDef(
            name=cst.Name(name), params=cst.Parameters(), body=body_block, decorators=decorators, returns=returns_node
        )

    def _normalize_body(self, body: str) -> List[str]:
        """Return non-empty lines from the body preserving indentation."""
        return [line for line in body.splitlines() if line.strip()]

    def _parse_statement_safe(self, line: str) -> cst.BaseStatement:
        """Parse a single statement; on error return a Pass statement node.

        This isolates the try/except so tests can assert the fallback behavior
        deterministically.
        """
        try:
            return parse_statement(line)
        except Exception:
            return cst.SimpleStatementLine(body=[cst.Pass()])

    def emit_fixture(self, name: str, body: str) -> cst.FunctionDef:
        return self.emit_fixture_node(name, body)

    def emit_composite_dirs_node(self, base_name: str, mapping: dict[str, str]) -> cst.FunctionDef:
        assigns: list[cst.BaseStatement] = []
        for k, expr_src in mapping.items():
            try:
                expr = cst.parse_expression(expr_src)
            except Exception:
                expr = cst.Name("None")
            assign = cst.SimpleStatementLine(
                body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name(k))], value=expr)]
            )
            assigns.append(assign)

        dict_entries: list[cst.DictElement] = []
        for k in mapping.keys():
            key = cst.SimpleString(f'"{k}"')
            value = cst.Name(k)
            dict_entries.append(cst.DictElement(key=key, value=value))
        dict_expr = cst.Dict(elements=dict_entries)

        yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Yield(value=dict_expr))])

        # Try(body, handlers, orelse, finalbody) - use a Finally node for finalbody
        try_node = cst.Try(
            body=cst.IndentedBlock(body=[yield_stmt]),
            handlers=[],
            orelse=None,
            finalbody=cst.Finally(body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])),
        )

        body_block = cst.IndentedBlock(body=[*assigns, try_node])
        decorators = [cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))]
        return cst.FunctionDef(
            name=cst.Name(base_name), params=cst.Parameters(), body=body_block, decorators=decorators
        )
