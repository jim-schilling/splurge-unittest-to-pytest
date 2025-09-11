import libcst as cst

from splurge_unittest_to_pytest.converter.setup_parser import parse_setup_assignments


def test_parse_setup_assignments_extracts_self_attrs():
    src = """
def setUp(self):
    self.foo = 1
    self.bar = 'x'
    other = 2
"""
    module = cst.parse_module(src)
    func = None
    for node in module.body:
        if isinstance(node, cst.FunctionDef) and node.name.value == "setUp":
            func = node
            break
    assert func is not None
    assignments = parse_setup_assignments(func)
    assert "foo" in assignments
    assert "bar" in assignments
    assert "other" not in assignments
