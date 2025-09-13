import libcst as cst

from splurge_unittest_to_pytest.converter.cleanup import extract_relevant_cleanup
from splurge_unittest_to_pytest.converter import cleanup


def test_extract_relevant_cleanup_call_and_assign():
    stmts = [
        cst.parse_statement("self.conn.close()"),
        cst.parse_statement("self.value = None"),
        cst.parse_statement("print('ok')"),
    ]
    res = extract_relevant_cleanup(stmts, "conn")
    assert len(res) == 1
    assert isinstance(res[0], cst.SimpleStatementLine)

    res2 = extract_relevant_cleanup(stmts, "value")
    assert len(res2) == 1


def test_extract_relevant_cleanup_if_block():
    stmt = cst.parse_statement("if self.ready:\n    self.conn.close()\nelse:\n    pass")
    res = extract_relevant_cleanup([stmt], "conn")
    # Should return the enclosing If node when inner matched
    assert len(res) == 1
    assert isinstance(res[0], cst.If)


def test_references_attribute_name_and_attr():
    assert cleanup.references_attribute(cst.Name("foo"), "foo")
    assert cleanup.references_attribute(cst.Attribute(value=cst.Name("self"), attr=cst.Name("foo")), "foo")


def test_references_attribute_in_call_args():
    call = cst.parse_expression("f(x, y, foo)")
    assert cleanup.references_attribute(call, "foo")


def test_extract_relevant_cleanup_finds_assign_and_if():
    src = """
foo()
if x == foo:
    bar()
other = 1
"""
    module = cst.parse_module(src)
    stmts = list(module.body)
    relevant = cleanup.extract_relevant_cleanup(stmts, "foo")
    # Should include the call and the if statement
    assert any(isinstance(s, cst.SimpleStatementLine) for s in relevant)
    assert any(isinstance(s, cst.If) for s in relevant)
