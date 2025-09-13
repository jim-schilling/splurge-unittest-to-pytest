import libcst as cst

from splurge_unittest_to_pytest.converter.cleanup_checks import references_attribute


def _expr(s: str) -> cst.CSTNode:
    return cst.parse_expression(s)


def test_name_matches():
    assert references_attribute(_expr("x"), "x")
    assert not references_attribute(_expr("y"), "x")


def test_attribute_chain():
    e = _expr("self.x")
    assert references_attribute(e, "x")
    # chained attribute
    e2 = _expr("obj.sub.x")
    assert references_attribute(e2, "x")


def test_call_func_and_args():
    e = _expr("foo(self.x, z)")
    assert references_attribute(e, "x")
    # function object itself references attribute
    e2 = _expr("self.method()")
    assert references_attribute(e2, "method")


def test_subscript_and_index():
    e = _expr("arr[self.i]")
    assert references_attribute(e, "i")
    e2 = _expr("d[0]")
    assert not references_attribute(e2, "i")


def test_binary_and_comparison_and_bool_ops():
    e = _expr("self.a + 1")
    assert references_attribute(e, "a")
    e2 = _expr("1 < self.b")
    assert references_attribute(e2, "b")
    e3 = _expr("self.c and d")
    assert references_attribute(e3, "c")


def test_sequence_containers():
    e = _expr("(a, self.x, 3)")
    assert references_attribute(e, "x")
