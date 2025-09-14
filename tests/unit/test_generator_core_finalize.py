import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.generator_core import GeneratorCore


def make_spec(name: str, expr_src: str, yield_style: bool = False):
    class S:
        pass

    s = S()
    s.name = name
    s.value_expr = cst.parse_expression(expr_src)
    s.cleanup_statements = []
    s.yield_style = yield_style
    return s


def test_finalize_attaches_list_typing():
    core = GeneratorCore()
    specs = {"a": make_spec("a", "[1,2]")}
    fn = cst.FunctionDef(name=cst.Name("a"), params=cst.Parameters(), body=cst.IndentedBlock(body=[]))
    res = core.finalize([], [fn], specs, bundler_typing=set())
    assert "needs_typing_names" in res
    assert "List" in res["needs_typing_names"]


def test_finalize_adds_generator_when_yield():
    core = GeneratorCore()
    specs = {"a": make_spec("a", "1", yield_style=True)}
    fn = cst.FunctionDef(name=cst.Name("a"), params=cst.Parameters(), body=cst.IndentedBlock(body=[]))
    res = core.finalize([], [fn], specs, bundler_typing=set())
    assert "Generator" in res.get("needs_typing_names", [])
