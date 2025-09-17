import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def test_simple_statement_multiple_small_statements_not_converted_bare():
    # multiple small statements on the same SimpleStatementLine should not convert
    src = """
def t():
    self.assertRaises(ValueError); x = 1
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class WF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_with = False

        def visit_With(self, node: cst.With) -> None:
            self.has_with = True

    wf = WF()
    out.visit(wf)
    assert not wf.has_with


def test_simple_statement_non_call_expr_not_converted():
    # a non-Call Expr small statement should be left alone
    src = """
def t():
    (1 + 2)
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    # no With nodes produced
    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_with = False

        def visit_With(self, node: cst.With) -> None:
            self.has_with = True

    f = Finder()
    out.visit(f)
    assert not f.has_with


def test_functional_single_arg_no_conversion():
    # functional form with only one arg (exc only) should not convert
    src = """
def t():
    self.assertRaises(ValueError)
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_with = False

        def visit_With(self, node: cst.With) -> None:
            self.found_with = True

    f = Finder()
    out.visit(f)
    assert not f.found_with
