import libcst as cst

from splurge_unittest_to_pytest.converter import helpers, imports


def test_self_reference_remover_replaces_self_attr():
    remover = helpers.SelfReferenceRemover({"self"})
    expr = cst.parse_expression("self.x")
    res = expr.visit(remover)
    assert isinstance(res, cst.Name)
    assert res.value == "x"


def test_remove_unittest_importfrom_and_import():
    mod_src = "from unittest import TestCase\nimport os\n"
    module = cst.parse_module(mod_src)
    new_body = []
    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine) and isinstance(stmt.body[0], cst.ImportFrom):
            out = imports.remove_unittest_importfrom(stmt.body[0])
            if out is not cst.RemovalSentinel.REMOVE:
                new_body.append(stmt)
        else:
            new_body.append(stmt)
    new_mod = cst.Module(body=new_body)
    code = new_mod.code
    assert "unittest" not in code
