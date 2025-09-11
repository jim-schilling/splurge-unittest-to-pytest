import libcst as cst

from splurge_unittest_to_pytest.stages.rewriter import rewriter_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def test_rewriter_inserts_self_param() -> None:
    src = """class A:
    def test_foo():
        pass
"""
    module = cst.parse_module(src)
    class_node = next(n for n in module.body if isinstance(n, cst.ClassDef))
    ci = ClassInfo(node=class_node)
    collector = CollectorOutput(module=module, module_docstring_index=None, imports=(), classes={"A": ci})
    out = rewriter_stage({"module": module, "collector_output": collector})
    new_mod = out.get("module")
    assert isinstance(new_mod, cst.Module)
    cls = next(n for n in new_mod.body if isinstance(n, cst.ClassDef) and n.name.value == "A")
    func = next(m for m in cls.body.body if isinstance(m, cst.FunctionDef) and m.name.value == "test_foo")
    assert func.params.params
    assert func.params.params[0].name.value in ("self", "cls")
