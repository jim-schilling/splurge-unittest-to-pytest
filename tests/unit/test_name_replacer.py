import libcst as cst

from splurge_unittest_to_pytest.converter.name_replacer import replace_names_in_statements


def test_replace_names_in_statements_replaces_attr_and_name():
    src = """
inst = self.some_attr
other = some_attr
"""
    module = cst.parse_module(src)
    stmts = list(module.body)

    replaced = replace_names_in_statements(stmts, "some_attr", "_some_attr_value")

    # Render back to code by placing statements into a Module
    mod = cst.Module(body=replaced)
    code = mod.code
    assert "_some_attr_value" in code
    assert "self.some_attr" not in code
