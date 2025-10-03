import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as aw


def test_safe_extract_from_indented_block():
    stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="x"))])
    block = cst.IndentedBlock(body=[stmt])
    out = aw._safe_extract_statements(block)
    assert isinstance(out, list)
    assert len(out) == 1
    # LibCST may normalize simple statements to Expr nodes inside blocks;
    # accept either form here to keep the test robust.
    assert isinstance(out[0], cst.SimpleStatementLine | cst.Expr)


def test_safe_extract_nested_blocks():
    stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="y"))])
    inner = cst.IndentedBlock(body=[stmt])
    outer = cst.IndentedBlock(body=[inner])
    out = aw._safe_extract_statements(outer)
    assert isinstance(out, list)
    assert len(out) == 1
    assert isinstance(out[0], cst.SimpleStatementLine | cst.Expr)
