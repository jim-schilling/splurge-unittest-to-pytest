import libcst as cst

from splurge_unittest_to_pytest.converter.name_replacer import (
    replace_names_in_statements,
)


def stmt_code(stmt: cst.BaseStatement) -> str:
    return cst.Module(body=[stmt]).code.strip()


def test_replace_attribute_and_keep_unrelated():
    stmts = [cst.parse_statement("return self.x + other")]
    out = replace_names_in_statements(stmts, "x", "x")
    assert len(out) == 1
    code = stmt_code(out[0])
    assert "return x + other" in code


def test_replace_only_attribute_occurrences():
    stmts = [cst.parse_statement("val = self.count + count")]
    out = replace_names_in_statements(stmts, "count", "count")
    code = stmt_code(out[0])
    # only self.count should be replaced
    assert "val = count + count" in code
    

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
