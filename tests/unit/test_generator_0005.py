import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.self_attr_finder import collect_self_attrs

DOMAINS = ["generator"]


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
