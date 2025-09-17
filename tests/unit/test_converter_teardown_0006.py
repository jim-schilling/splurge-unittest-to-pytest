import libcst as cst

from splurge_unittest_to_pytest.converter.cleanup_inspect import simple_stmt_references_attribute

DOMAINS = ["converter", "teardown"]


def test_call_func_and_args_reference():
    stmt = cst.parse_statement("print(self.x)")
    assert simple_stmt_references_attribute(stmt, "x")


def test_expr_non_call_reference():
    stmt = cst.parse_statement("self.y")
    assert simple_stmt_references_attribute(stmt, "y")


def test_assign_target_reference():
    stmt = cst.parse_statement("self.z = 1")
    assert simple_stmt_references_attribute(stmt, "z")


def test_empty_stmt_returns_false():
    stmt = cst.SimpleStatementLine(body=[])
    assert not simple_stmt_references_attribute(stmt, "x")
