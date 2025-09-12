import libcst as cst

from splurge_unittest_to_pytest.converter.cleanup_checks import references_attribute
from splurge_unittest_to_pytest.converter.cleanup import extract_relevant_cleanup


def test_references_attribute_simple_attribute_and_name():
    a = cst.parse_expression("self.x")
    assert references_attribute(a, "x")
    n = cst.parse_expression("x")
    assert references_attribute(n, "x")


def test_references_attribute_call_and_args():
    expr = cst.parse_expression("f(self.x, other)")
    assert references_attribute(expr, "x")


def test_references_attribute_subscript_and_tuple():
    expr = cst.parse_expression("a[self.x, (b, c)]")
    assert references_attribute(expr, "x")


def test_references_attribute_binary_and_comparison():
    expr = cst.parse_expression("(self.x + 1) == other")
    assert references_attribute(expr, "x")


def test_extract_relevant_cleanup_finds_if_and_assign():
    if_stmt = cst.parse_statement("if self.v:\n    a = 1\n")
    assign = cst.parse_statement("self.v = 2")
    other = cst.parse_statement("print(1)")
    res = extract_relevant_cleanup([if_stmt, assign, other], "v")
    # should include the If and the Assign (Assigns are returned as SimpleStatementLine)
    assert any(isinstance(s, cst.If) for s in res)
    assert any(isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], cst.Assign) for s in res)
