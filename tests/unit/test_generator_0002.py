import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.generator_core import GeneratorCore


def test_make_composite_dirs_fixture_emits_node():
    core = GeneratorCore()
    node = core.make_composite_dirs_fixture("base", {"a": "1", "b": "2"})
    assert isinstance(node, cst.FunctionDef)


def test_finalize_collects_typing_and_yield():
    core = GeneratorCore()

    class FakeSpec:
        def __init__(self, name, value_expr, *, yield_style=False):
            self.name = name
            self.value_expr = value_expr
            self.yield_style = yield_style

    specs = {"a": FakeSpec("a", cst.List([])), "b": FakeSpec("b", None)}
    res = core.finalize([], [], specs)
    assert "needs_typing_names" in res
    assert any((n in res["needs_typing_names"] for n in ("List", "Any")))
