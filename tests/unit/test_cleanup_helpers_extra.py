import libcst as cst

from splurge_unittest_to_pytest.converter.cleanup import extract_relevant_cleanup
from splurge_unittest_to_pytest.converter.cleanup_inspect import simple_stmt_references_attribute


def test_simple_stmt_references_call_and_args():
    stmt = cst.parse_statement("print(self.x)")
    assert isinstance(stmt, cst.SimpleStatementLine)
    assert simple_stmt_references_attribute(stmt, 'x')


def test_extract_relevant_cleanup_if_and_nested():
    src = """
if cond:
    print(self.a)
else:
    pass
"""
    module = cst.parse_module(src)
    stmts = list(module.body)
    relevant = extract_relevant_cleanup(stmts, 'a')
    # The enclosing If should be returned because inner print references attr
    assert any(isinstance(s, cst.If) for s in relevant)


def test_extract_relevant_cleanup_with_indented_block():
    # Build an indented block manually
    inner = cst.parse_statement("print(self.y)")
    block = cst.IndentedBlock(body=[inner])
    relevant = extract_relevant_cleanup([block], 'y')
    # The implementation returns the inner statement when found
    assert any(isinstance(s, cst.SimpleStatementLine) for s in relevant)
