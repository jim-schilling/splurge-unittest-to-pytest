import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def test_exception_attr_rewriter_rewrites_unshadowed():
    src = """
import pytest

cm = object()
def t():
    pass

x = cm.exception
"""
    module = cst.parse_module(src)
    new = module.visit(raises_stage.ExceptionAttrRewriter("cm"))

    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.attr = None

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm":
                    if isinstance(node.attr, cst.Name):
                        self.attr = node.attr.value
            except Exception:
                pass

    af = AF()
    new.visit(af)
    assert af.attr == "value"


def test_exception_attr_rewriter_respects_posonly_and_kwonly_params():
    # posonly param
    src_pos = """
def f(cm, /):
    return cm.exception
"""
    module_pos = cst.parse_module(src_pos)
    out_pos = module_pos.visit(raises_stage.ExceptionAttrRewriter("cm"))

    class FinderPos(cst.CSTVisitor):
        def __init__(self) -> None:
            self.inner_attr = None

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.attr, cst.Name):
                    self.inner_attr = node.attr.value
            except Exception:
                pass

    fp = FinderPos()
    out_pos.visit(fp)
    # param binds cm, so attribute inside should remain 'exception'
    assert fp.inner_attr == "exception"

    # kwonly param
    src_kw = """
def f(*, cm):
    return cm.exception
"""
    module_kw = cst.parse_module(src_kw)
    out_kw = module_kw.visit(raises_stage.ExceptionAttrRewriter("cm"))
    fk = FinderPos()
    out_kw.visit(fk)
    assert fk.inner_attr == "exception"


def test_raises_stage_returns_needs_pytest_import_true_for_conversion():
    src = """
def t():
    self.assertRaises(ValueError, func, 1)
"""
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is True


def test_exceptioninfo_normalizer_stage_lambda_shadowing():
    src = """
import pytest

with pytest.raises(ValueError) as cm:
    pass

f = lambda cm: cm.exception
g = cm.exception
"""
    module = cst.parse_module(src)
    out = raises_stage.exceptioninfo_normalizer_stage({"module": module})
    new = out.get("module")

    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.lambda_attr = None
            self.outer_attr = None

        def visit_Lambda(self, node: cst.Lambda) -> None:
            try:
                if isinstance(node.body, cst.Attribute) and isinstance(node.body.attr, cst.Name):
                    self.lambda_attr = node.body.attr.value
            except Exception:
                pass

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm":
                    if isinstance(node.attr, cst.Name):
                        self.outer_attr = node.attr.value
            except Exception:
                pass

    af = AF()
    new.visit(af)
    assert af.lambda_attr == "exception"
    assert af.outer_attr == "value"
