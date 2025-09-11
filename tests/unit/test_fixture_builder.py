import libcst as cst

from splurge_unittest_to_pytest.converter.fixture_builder import (
    replace_attr_references_in_statements,
)


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
