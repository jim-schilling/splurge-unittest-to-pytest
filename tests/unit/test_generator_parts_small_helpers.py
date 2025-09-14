from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.dependency_finder import collect_self_attributes
from splurge_unittest_to_pytest.stages.generator_parts.transformers import ReplaceSelfWithName, ReplaceNameWithLocal


def test_collect_self_attributes_simple() -> None:
    mod = cst.parse_module("""
class A:
    def f(self):
        x = self.foo
        y = self.bar.baz(self.qux)
""")
    attrs = collect_self_attributes(mod)
    assert "foo" in attrs
    assert "bar" in attrs
    assert "qux" in attrs


def test_replace_self_with_name_and_name_local() -> None:
    expr = cst.parse_expression("self.dir.mkdir(parents=True)")
    new = expr.visit(ReplaceSelfWithName())
    assert isinstance(new, cst.Call)
    # name replaced
    assert "dir.mkdir" not in cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(new)])]).code

    # ReplaceNameWithLocal
    stmt = cst.parse_statement("x = foo")
    stmt2 = stmt.visit(ReplaceNameWithLocal("foo", "_foo_value"))
    assert "_foo_value" in cst.Module(body=[stmt2]).code
