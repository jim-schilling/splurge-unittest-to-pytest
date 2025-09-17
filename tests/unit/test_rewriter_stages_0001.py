"""Test the flexible parameter handling for different method types."""

import libcst as cst
from typing import cast
from splurge_unittest_to_pytest.stages.rewriter import rewriter_stage
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


class TestFlexibleParameterHandling:
    """Test that the `rewriter_stage` produces correct parameter lists."""

    def _make_class_module(self, func_def_src: str) -> str:
        return f"\nimport unittest\n\nclass T(unittest.TestCase):\n{func_def_src}\n"

    def _convert_and_get_params(self, src: str) -> list[str]:
        """Convert class source and return parameter name list."""
        mod = cst.parse_module(src)
        ctx = {"module": mod, "collector_output": None}
        fake = type("F", (), {})()
        fake.classes = {"T": type("CI", (), {"setup_assignments": {}})()}
        ctx["collector_output"] = fake
        res = rewriter_stage(ctx)
        new_mod = cast(cst.Module, res.get("module"))
        for node in new_mod.body:
            if isinstance(node, cst.ClassDef) and node.name.value == "T":
                for item in node.body.body:
                    if isinstance(item, cst.FunctionDef):
                        return [p.name.value for p in item.params.params]
        return []

    def test_instance_method_inserts_self(self) -> None:
        src = "    def test_one(self, arg1):\n        pass\n"
        params = self._convert_and_get_params(self._make_class_module(src))
        assert params[0] in ("self",)

    def test_classmethod_inserts_cls(self) -> None:
        src = "    @classmethod\n    def test_one(cls, arg1):\n        pass\n"
        params = self._convert_and_get_params(self._make_class_module(src))
        assert params[0] == "cls"

    def test_staticmethod_keeps_params(self) -> None:
        src = "    @staticmethod\n    def test_one(arg1, arg2):\n        pass\n"
        params = self._convert_and_get_params(self._make_class_module(src))
        assert params == ["arg1", "arg2"]


SAMPLE = "\nclass MyTests(unittest.TestCase):\n    def setUp(self) -> None:\n        self.a = 1\n        self.b = 'x'\n\n    def test_one(self) -> None:\n        assert self.a == 1\n"


def test_rewriter_adds_fixture_params_and_removes_self() -> None:
    module = cst.parse_module(SAMPLE)
    visitor = Collector()
    module.visit(visitor)
    co = visitor.as_output()
    ctx = {"module": module, "collector_output": co}
    res = rewriter_stage(ctx)
    new_mod = cast(cst.Module, res.get("module"))
    cls = [n for n in new_mod.body if isinstance(n, cst.ClassDef) and n.name.value == "MyTests"][0]
    func = [m for m in cls.body.body if isinstance(m, cst.FunctionDef) and m.name.value == "test_one"][0]
    param_names = [p.name.value for p in func.params.params]
    assert "self" not in param_names and "cls" not in param_names
    assert "a" in param_names and "b" in param_names


def test_rewriter_inserts_self_param() -> None:
    src = "class A:\n    def test_foo():\n        pass\n"
    module = cst.parse_module(src)
    class_node = next((n for n in module.body if isinstance(n, cst.ClassDef)))
    ci = ClassInfo(node=class_node)
    collector = CollectorOutput(module=module, module_docstring_index=None, imports=(), classes={"A": ci})
    out = rewriter_stage({"module": module, "collector_output": collector})
    new_mod = out.get("module")
    assert isinstance(new_mod, cst.Module)
    cls = next((n for n in new_mod.body if isinstance(n, cst.ClassDef) and n.name.value == "A"))
    func = next((m for m in cls.body.body if isinstance(m, cst.FunctionDef) and m.name.value == "test_foo"))
    assert func.params.params
    assert func.params.params[0].name.value in ("self", "cls")
