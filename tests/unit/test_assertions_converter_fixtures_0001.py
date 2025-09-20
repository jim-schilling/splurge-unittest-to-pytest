import libcst as cst

from splurge_unittest_to_pytest.converter.assertion_dispatch import convert_assertion
from splurge_unittest_to_pytest.converter.assertions import _assert_equal, _assert_is_none
from splurge_unittest_to_pytest.converter.fixtures import create_simple_fixture
from tests.unit.helpers.autouse_helpers import insert_attach_fixture_into_module, make_autouse_attach


def _arg_from_expr(src: str) -> cst.Arg:
    expr = cst.parse_expression(src)
    return cst.Arg(value=expr)


def test_assert_equal_direct_helper():
    a1 = _arg_from_expr("1")
    a2 = _arg_from_expr("2")
    node = _assert_equal([a1, a2])
    assert isinstance(node, cst.Assert)
    assert isinstance(node.test, cst.Comparison)
    comps = node.test.comparisons
    assert len(comps) == 1
    assert isinstance(comps[0].operator, cst.Equal)
    assert isinstance(comps[0].comparator, cst.Integer)


def test_convert_assertion_via_map():
    a1 = _arg_from_expr("x")
    a2 = _arg_from_expr("y")
    res = convert_assertion("assertEqual", [a1, a2])
    assert isinstance(res, cst.Assert)


def test_assert_is_none_returns_none_for_literals():
    a1 = _arg_from_expr("1")
    node = _assert_is_none([a1])
    assert node is None


def test_create_simple_fixture_and_autouse_attach_insertion():
    val_expr = cst.parse_expression("42")
    fixture = create_simple_fixture("my_fixture", val_expr)
    assert isinstance(fixture, cst.FunctionDef)
    module = cst.parse_module("\n")

    def _make_autouse_attach_local(setup_fixtures: dict[str, cst.FunctionDef]) -> cst.FunctionDef:
        inst_assign = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("inst"))],
                    value=cst.Call(
                        func=cst.Name("getattr"),
                        args=[
                            cst.Arg(value=cst.Name("request")),
                            cst.Arg(value=cst.SimpleString("'instance'")),
                            cst.Arg(value=cst.Name("None")),
                        ],
                    ),
                )
            ]
        )
        set_calls: list[cst.BaseStatement] = []
        for name in setup_fixtures.keys():
            set_calls.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Expr(
                            value=cst.Call(
                                func=cst.Name("setattr"),
                                args=[
                                    cst.Arg(value=cst.Name("inst")),
                                    cst.Arg(value=cst.SimpleString(f"'{name}'")),
                                    cst.Arg(value=cst.Name(name)),
                                ],
                            )
                        )
                    ]
                )
            )
        if_block = cst.IndentedBlock(body=set_calls)
        if_stmt = cst.If(
            test=cst.Comparison(
                left=cst.Name("inst"),
                comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))],
            ),
            body=if_block,
        )
        from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator

        decorator = build_pytest_fixture_decorator({"autouse": True})
        func = cst.FunctionDef(
            name=cst.Name("_attach_to_instance"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("request"))]),
            body=cst.IndentedBlock(body=[inst_assign, if_stmt]),
            decorators=[decorator],
        )
        return func

    def _insert_attach_fixture_local(module_node: cst.Module, fixture_func: cst.FunctionDef) -> cst.Module:
        new_body: list = list(module_node.body)
        insert_pos = 0
        for i, stmt in enumerate(new_body):
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                first = stmt.body[0]
                if isinstance(first, cst.Import):
                    for alias in first.names:
                        if isinstance(alias.name, cst.Name) and alias.name.value == "pytest":
                            insert_pos = i + 1
                            break
                if insert_pos:
                    break
        new_body.insert(insert_pos, cst.EmptyLine())
        new_body.insert(insert_pos + 1, fixture_func)
        new_module = module_node.with_changes(body=new_body)
        return new_module

    autouse_fn = make_autouse_attach({"my_fixture": fixture})
    mod2 = insert_attach_fixture_into_module(module, autouse_fn)
    found = any((isinstance(s, cst.FunctionDef) and s.name.value == "_attach_to_instance" for s in mod2.body))
    assert found
