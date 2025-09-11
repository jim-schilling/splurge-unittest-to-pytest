import libcst as cst

from splurge_unittest_to_pytest.converter.fixture_builder import replace_attr_references_in_statements


def test_replace_attr_references_replaces_name_and_attribute():
    src = """foo = bar\ninst = self.baz\n"""
    module = cst.parse_module(src)
    stmts = list(module.body)
    replaced = replace_attr_references_in_statements(stmts, "baz", "_baz_value")
    mod = cst.Module(body=replaced)
    code = mod.code
    assert "_baz_value" in code
    assert "self.baz" not in code



def _parse_stmt(src: str) -> cst.BaseStatement:
    mod = cst.parse_module(src)
    return mod.body[0].body[0]


def test_replace_bare_name():
    stmt = _parse_stmt("x = attr")
    out = replace_attr_references_in_statements([stmt], "attr", "_attr_value")
    # Expect the Name 'attr' replaced with '_attr_value' when rendered
    code = cst.Module([]).code_for_node(out[0])
    assert "_attr_value" in code


def test_replace_self_attribute():
    stmt = _parse_stmt("self.attr.close()")
    out = replace_attr_references_in_statements([stmt], "attr", "_attr_value")
    assert "_attr_value" in cst.Module([]).code_for_node(out[0])
