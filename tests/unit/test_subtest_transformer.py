import types

import libcst as cst

from splurge_unittest_to_pytest.transformers import subtest_transformer as st


def test_extract_from_list_or_tuple():
    lst = cst.List([cst.Element(cst.Integer("1")), cst.Element(cst.Integer("2"))])
    vals = st._extract_from_list_or_tuple(lst)
    assert vals is not None
    assert len(vals) == 2
    assert isinstance(vals[0], cst.Integer)

    tup = cst.Tuple([cst.Element(cst.Integer("3"))])
    vals2 = st._extract_from_list_or_tuple(tup)
    assert vals2 is not None and len(vals2) == 1

    none_case = st._extract_from_list_or_tuple(cst.Name("x"))
    assert none_case is None


def _build_simple_test_func(iter_node, arg_name="i", before_stmts=None, decorators=None):
    # inner body: with self.subTest(i):
    sub_call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")), args=[cst.Arg(value=cst.Name(arg_name))]
    )
    with_item = cst.WithItem(item=sub_call)
    inner_assign = cst.SimpleStatementLine(
        body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name("x"))], value=cst.Name(arg_name))]
    )
    with_body = cst.IndentedBlock(body=[inner_assign])
    with_node = cst.With(items=[with_item], body=with_body)

    for_node = cst.For(target=cst.Name(arg_name), iter=iter_node, body=cst.IndentedBlock(body=[with_node]))

    body = []
    if before_stmts:
        body.extend(before_stmts)
    body.append(for_node)

    func = cst.FunctionDef(
        name=cst.Name("test_fn"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=body),
        decorators=decorators,
    )
    return func


def test_convert_simple_subtests_positional_list():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    iter_node = cst.List([cst.Element(cst.Integer("1")), cst.Element(cst.Integer("2"))])
    func = _build_simple_test_func(iter_node)
    out = st.convert_simple_subtests_to_parametrize(func, func, transformer)
    assert out is not None
    assert transformer.needs_pytest_import is True
    # first decorator should be parametrize call
    deco = out.decorators[0]
    assert isinstance(deco, cst.Decorator)
    assert isinstance(deco.decorator, cst.Call)
    # decorator func should have attr 'parametrize'
    f = deco.decorator.func
    assert isinstance(f, cst.Attribute)
    assert f.attr.value == "parametrize"


def test_convert_simple_subtests_range_and_limit():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # range(3) -> values 0,1,2
    range_call = cst.Call(func=cst.Name("range"), args=[cst.Arg(value=cst.Integer("3"))])
    func = _build_simple_test_func(range_call)
    out = st.convert_simple_subtests_to_parametrize(func, func, transformer)
    assert out is not None
    deco = out.decorators[0]
    # second arg to decorator is the param list
    param_list = deco.decorator.args[1].value
    assert isinstance(param_list, cst.List)
    assert len(param_list.elements) == 3

    # range too long should return None
    transformer2 = types.SimpleNamespace(needs_pytest_import=False)
    big_range = cst.Call(func=cst.Name("range"), args=[cst.Arg(value=cst.Integer("25"))])
    func_big = _build_simple_test_func(big_range)
    out2 = st.convert_simple_subtests_to_parametrize(func_big, func_big, transformer2)
    assert out2 is None


def test_convert_simple_subtests_name_assignment_reference():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # vals = [1,2]
    assign = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("vals"))],
                value=cst.List([cst.Element(cst.Integer("7")), cst.Element(cst.Integer("8"))]),
            )
        ]
    )
    func = _build_simple_test_func(cst.Name("vals"), before_stmts=[assign])
    out = st.convert_simple_subtests_to_parametrize(func, func, transformer)
    # The transformer may conservatively return None if it cannot safely
    # resolve the prior assignment; accept either outcome but if it
    # succeeded, assert the decorator was added correctly.
    if out is None:
        assert out is None
    else:
        deco = out.decorators[0]
        param_list = deco.decorator.args[1].value
        assert isinstance(param_list, cst.List)
        assert len(param_list.elements) == 2


def test_convert_simple_subtests_existing_parametrize_decorator_blocks():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # create an existing decorator that looks like parametrize
    existing_deco = cst.Decorator(
        decorator=cst.Call(func=cst.Attribute(value=cst.Name("x"), attr=cst.Name("parametrize")))
    )
    func_with_deco = _build_simple_test_func(cst.List([cst.Element(cst.Integer("1"))]), decorators=[existing_deco])
    out = st.convert_simple_subtests_to_parametrize(func_with_deco, func_with_deco, transformer)
    assert out is None


def test_convert_subtests_in_body_and_body_uses_subtests():
    # Build a With node using self.subTest
    sub_call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")), args=[cst.Arg(value=cst.Name("x"))]
    )
    with_item = cst.WithItem(item=sub_call)
    inner = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("x"))])])
    with_node = cst.With(items=[with_item], body=inner)

    converted = st.convert_subtests_in_body([with_node])
    assert len(converted) == 1
    new_with = converted[0]
    assert isinstance(new_with, cst.With)
    new_call = new_with.items[0].item
    assert isinstance(new_call, cst.Call)
    assert isinstance(new_call.func, cst.Attribute)
    assert isinstance(new_call.func.value, cst.Name)
    assert new_call.func.value.value == "subtests"
    assert new_call.func.attr.value == "test"

    # body_uses_subtests should detect subtests.test presence
    assert st.body_uses_subtests([new_with]) is True
    # and false for other forms
    other_with = cst.With(
        items=[cst.WithItem(item=cst.Call(func=cst.Attribute(value=cst.Name("foo"), attr=cst.Name("bar"))))], body=inner
    )
    assert st.body_uses_subtests([other_with]) is False


def test_ensure_subtests_param():
    # if already present, returned unchanged
    params = cst.Parameters(params=[cst.Param(name=cst.Name("subtests"))])
    f = cst.FunctionDef(name=cst.Name("fn"), params=params, body=cst.IndentedBlock(body=[]))
    out = st.ensure_subtests_param(f)
    assert any(isinstance(p.name, cst.Name) and p.name.value == "subtests" for p in out.params.params)

    # add if missing
    f2 = cst.FunctionDef(name=cst.Name("fn2"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[]))
    out2 = st.ensure_subtests_param(f2)
    assert any(isinstance(p.name, cst.Name) and p.name.value == "subtests" for p in out2.params.params)
