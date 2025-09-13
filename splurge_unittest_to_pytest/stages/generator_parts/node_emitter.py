import libcst as cst
from libcst import parse_statement


class NodeEmitter:
    """Emit libcst AST nodes for fixtures from small body source strings.

    The emitter creates a FunctionDef node from simple lines or builds a
    composite dirs fixture when requested.
    """

    def emit_fixture_node(self, name: str, body: str) -> cst.FunctionDef:
        stmts: list[cst.BaseStatement] = []
        for line in body.splitlines():
            if not line.strip():
                continue
            try:
                stmt = parse_statement(line)
            except Exception:
                stmt = cst.SimpleStatementLine(body=[cst.Pass()])

            # parse_statement() returns either a BaseSmallStatement (e.g. a
            # SimpleStatementLine) or a BaseCompoundStatement (e.g. If, Try).
            # IndentedBlock accepts a sequence of BaseStatement (either
            # small or compound), so append the parsed node directly. Do not
            # attempt to wrap a compound statement inside a SimpleStatementLine
            # (that would be invalid).
            stmts.append(stmt)

        body_block = cst.IndentedBlock(body=stmts)

        decorators: list[cst.Decorator] = []
        if any("yield" in line or "try:" in line for line in body.splitlines()):
            decorators = [cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))]

        return cst.FunctionDef(name=cst.Name(name), params=cst.Parameters(), body=body_block, decorators=decorators)

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
