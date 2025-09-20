import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.cleanup_checks import is_simple_cleanup_statement
from splurge_unittest_to_pytest.stages.generator_parts.generator_core import GeneratorCore
from splurge_unittest_to_pytest.stages.generator_parts.references_attr import references_attribute
from splurge_unittest_to_pytest.stages.generator_parts.replace_self_param import ReplaceSelfWithParam
from splurge_unittest_to_pytest.stages.generator_parts.self_attr_finder import collect_self_attrs


def s(src: str):
    return cst.parse_statement(src)


def test_assign_self_attr():
    st = s("self.x = 1")
    assert is_simple_cleanup_statement(st, "x")


def test_assign_bare_name():
    st = s("x = None")
    assert is_simple_cleanup_statement(st, "x")


def test_expr_wrapped_assign():
    st = s("(foo())")
    assert not is_simple_cleanup_statement(st, "x")


def test_delete_by_name():
    st = s("del self.x")
    assert isinstance(is_simple_cleanup_statement(st, "x"), bool)


def make_spec(name: str, expr_src: str, *, yield_style: bool = False):
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


def expr(src: str):
    return cst.parse_expression(src)


def test_bare_name_matches():
    assert references_attribute(expr("x"), "x")
    assert not references_attribute(expr("y"), "x")


def test_self_attribute_matches():
    assert references_attribute(expr("self.x"), "x")
    assert references_attribute(expr("cls.x"), "x")


def test_in_call_and_args():
    assert references_attribute(expr("foo(self.x)"), "x")
    assert references_attribute(expr("foo(a, self.x, b)"), "x")


def test_subscript_and_slices():
    assert references_attribute(expr("a[self.x]"), "x")
    assert references_attribute(expr("a[b:self.x]"), "x")


def test_ops_and_collections():
    assert references_attribute(expr("self.x + 1"), "x")
    assert references_attribute(expr("[self.x, 1]"), "x")
    assert not references_attribute(expr("[1,2]"), "x")


def parse_expr(src: str) -> cst.BaseExpression:
    return cst.parse_expression(src)


def test_replace_self_with_param_replaces():
    expr = parse_expr("self.foo")
    rewritten = expr.visit(ReplaceSelfWithParam({"foo"}))
    assert isinstance(rewritten, cst.Name)
    assert rewritten.value == "foo"


def test_replace_non_self_preserved():
    expr = parse_expr("obj.bar")
    rewritten = expr.visit(ReplaceSelfWithParam({"bar"}))
    assert isinstance(rewritten, cst.Attribute)


def test_collect_simple_attr():
    expr = cst.Attribute(value=cst.Name("self"), attr=cst.Name("x"))
    assert collect_self_attrs(expr) == {"x"}


def test_collect_nested_in_call():
    expr = cst.Call(
        func=cst.Name("str"),
        args=[
            cst.Arg(
                value=cst.BinaryOperation(
                    left=cst.Attribute(value=cst.Name("self"), attr=cst.Name("log_dir")),
                    operator=cst.BitOr(),
                    right=cst.SimpleString('"a"'),
                )
            )
        ],
    )
    assert collect_self_attrs(expr) == {"log_dir"}


def test_collect_in_dict():
    expr = cst.Dict(
        elements=[
            cst.DictElement(key=cst.SimpleString('"k"'), value=cst.Attribute(value=cst.Name("cls"), attr=cst.Name("v")))
        ]
    )
    assert collect_self_attrs(expr) == {"v"}
