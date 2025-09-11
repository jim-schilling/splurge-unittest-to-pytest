import libcst as cst

from splurge_unittest_to_pytest.converter.cleanup_inspect import (
    simple_stmt_references_attribute,
)


def test_simple_call_references():
    stmt = cst.parse_statement("self.conn.close()")
    assert simple_stmt_references_attribute(stmt, "conn")


def test_simple_assign_references():
    stmt = cst.parse_statement("self.value = 1")
    assert simple_stmt_references_attribute(stmt, "value")


def test_simple_expr_no_reference():
    stmt = cst.parse_statement("print('ok')")
    assert not simple_stmt_references_attribute(stmt, "value")
