import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from splurge_unittest_to_pytest.transformers.transformer_helper import ReplacementApplier, ReplacementRegistry


def make_position_wrapper(code: str) -> cst.Module:
    """Helper to parse code and return a MetadataWrapper around the module."""
    module = cst.parse_module(code)
    return MetadataWrapper(module)


def test_replacement_registry_record_and_get():
    code = """
x = 1
"""
    wrapper = make_position_wrapper(code)
    module = wrapper.module

    # find the Name node 'x' assignment target
    assign = module.body[0]
    assert isinstance(assign, cst.SimpleStatementLine)
    target = assign.body[0]
    assert isinstance(target, cst.Assign)


def test_apply_call_expression_replacement():
    # Create a simple call expression and record a replacement expression
    code = """
print('a')
"""
    wrapper = make_position_wrapper(code)
    module = wrapper.module

    # Locate the Call node
    stmt = module.body[0]
    assert isinstance(stmt, cst.SimpleStatementLine)
    expr = stmt.body[0]
    assert isinstance(expr, cst.Expr)
    call = expr.value
    assert isinstance(call, cst.Call)

    # Record replacement for the call expression with a Name expression
    registry = ReplacementRegistry()
    pos = wrapper.resolve(PositionProvider)[call]
    registry.record(pos, cst.Name(value="REPLACED"))

    # Apply ReplacementApplier
    applier = ReplacementApplier(registry)
    # Use the MetadataWrapper to run the transformer so metadata APIs are available
    new_module = wrapper.visit(applier)

    # After applying, the expression should be replaced
    new_stmt = new_module.body[0]
    assert isinstance(new_stmt, cst.SimpleStatementLine)
    new_expr = new_stmt.body[0]
    assert isinstance(new_expr, cst.Expr)
    assert isinstance(new_expr.value, cst.Name)
    assert new_expr.value.value == "REPLACED"


def test_apply_statement_replacement():
    # Replace a top-level call statement with an Assert statement
    code = """
foo()
"""
    wrapper = make_position_wrapper(code)
    module = wrapper.module

    stmt = module.body[0]
    expr = stmt.body[0]
    call = expr.value

    registry = ReplacementRegistry()
    pos = wrapper.resolve(PositionProvider)[call]
    # replacement is a SimpleStatementLine containing an Assert
    new_assert = cst.Assert(test=cst.Name("cond"))
    registry.record(pos, cst.SimpleStatementLine(body=[new_assert]))

    applier = ReplacementApplier(registry)
    # Use the MetadataWrapper to run the transformer so metadata APIs are available
    new_module = wrapper.visit(applier)

    new_stmt = new_module.body[0]
    # Should now be an Assert statement
    assert isinstance(new_stmt, cst.SimpleStatementLine)
    inner = new_stmt.body[0]
    assert isinstance(inner, cst.Assert)
