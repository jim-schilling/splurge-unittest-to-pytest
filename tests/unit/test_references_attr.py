import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.references_attr import references_attribute


def expr(src: str):
    return cst.parse_expression(src)


def test_bare_name_matches():
    assert references_attribute(expr("x"), "x")
    assert not references_attribute(expr("y"), "x")


def test_self_attribute_matches():
    assert references_attribute(expr("self.x"), "x")
    assert references_attribute(expr("cls.x"), "x")


def test_in_call_and_args():
    assert references_attribute(expr("foo(self.x)"), "x")
    assert references_attribute(expr("foo(a, self.x, b)"), "x")


def test_subscript_and_slices():
    assert references_attribute(expr("a[self.x]"), "x")
    assert references_attribute(expr("a[b:self.x]"), "x")


def test_ops_and_collections():
    assert references_attribute(expr("self.x + 1"), "x")
    assert references_attribute(expr("[self.x, 1]"), "x")
    assert not references_attribute(expr("[1,2]"), "x")
