import libcst as cst

from splurge_unittest_to_pytest.converter import cleanup


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
