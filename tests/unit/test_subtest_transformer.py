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


def _annotation_code(param: cst.Param) -> str:
    assert param.annotation is not None
    return cst.Module(body=[]).code_for_node(param.annotation.annotation)


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
    assert len(deco.decorator.args) == 3
    ids_arg = deco.decorator.args[2]
    assert isinstance(ids_arg.keyword, cst.Name)
    assert ids_arg.keyword.value == "ids"
    param = next(p for p in out.params.params if isinstance(p.name, cst.Name) and p.name.value == "i")
    assert _annotation_code(param) == "int"


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
    ids_arg = deco.decorator.args[2]
    assert isinstance(ids_arg.keyword, cst.Name)
    assert ids_arg.keyword.value == "ids"

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
                targets=[cst.AssignTarget(target=cst.Name("cases"))],
                value=cst.List(
                    [
                        cst.Element(
                            cst.Dict(
                                elements=[
                                    cst.DictElement(
                                        cst.SimpleString('"email"'), cst.SimpleString('"alpha@example.com"')
                                    ),
                                    cst.DictElement(cst.SimpleString('"active"'), cst.Name("True")),
                                ]
                            )
                        ),
                        cst.Element(
                            cst.Dict(
                                elements=[
                                    cst.DictElement(
                                        cst.SimpleString('"email"'), cst.SimpleString('"beta@example.org"')
                                    ),
                                    cst.DictElement(cst.SimpleString('"active"'), cst.Name("False")),
                                ]
                            )
                        ),
                    ]
                ),
            )
        ]
    )
    func = _build_simple_test_func(cst.Name("cases"), arg_name="case", before_stmts=[assign])
    out = st.convert_simple_subtests_to_parametrize(func, func, transformer)
    assert out is not None
    deco = out.decorators[0]
    param_list = deco.decorator.args[1].value
    assert isinstance(param_list, cst.List)
    assert len(param_list.elements) == 2
    # the prior assignment should be removed from the body
    assert all(
        not (
            isinstance(stmt, cst.SimpleStatementLine)
            and any(
                isinstance(small, cst.Assign)
                and isinstance(small.targets[0].target, cst.Name)
                and small.targets[0].target.value == "vals"
                for small in stmt.body
            )
        )
        for stmt in out.body.body
    )
    case_param = next(p for p in out.params.params if isinstance(p.name, cst.Name) and p.name.value == "case")
    assert _annotation_code(case_param) == "dict[str, object]"


def test_convert_simple_subtests_existing_parametrize_decorator_blocks():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # create an existing decorator that looks like parametrize
    existing_deco = cst.Decorator(
        decorator=cst.Call(func=cst.Attribute(value=cst.Name("x"), attr=cst.Name("parametrize")))
    )
    func_with_deco = _build_simple_test_func(cst.List([cst.Element(cst.Integer("1"))]), decorators=[existing_deco])
    out = st.convert_simple_subtests_to_parametrize(func_with_deco, func_with_deco, transformer)
    assert out is None


def test_convert_simple_subtests_tuple_target():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    iter_node = cst.List(
        [
            cst.Element(
                value=cst.Tuple(
                    [
                        cst.Element(cst.SimpleString('"GET"')),
                        cst.Element(cst.Integer("200")),
                    ]
                )
            ),
            cst.Element(
                value=cst.Tuple(
                    [
                        cst.Element(cst.SimpleString('"POST"')),
                        cst.Element(cst.Integer("201")),
                    ]
                )
            ),
        ]
    )
    for_target = cst.Tuple([cst.Element(value=cst.Name("left")), cst.Element(value=cst.Name("right"))])
    sub_call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")),
        args=[cst.Arg(keyword=cst.Name("member"), value=cst.Name("left"))],
    )
    with_item = cst.WithItem(item=sub_call)
    with_body = cst.IndentedBlock(
        body=[
            cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[cst.AssignTarget(target=cst.Name("result"))],
                        value=cst.Tuple(
                            [
                                cst.Element(cst.Name("left")),
                                cst.Element(cst.Name("right")),
                            ]
                        ),
                    )
                ]
            )
        ]
    )
    with_node = cst.With(items=[with_item], body=with_body)
    loop = cst.For(target=for_target, iter=iter_node, body=cst.IndentedBlock(body=[with_node]))
    func = cst.FunctionDef(
        name=cst.Name("test_pairs"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=[loop]),
    )
    out = st.convert_simple_subtests_to_parametrize(func, func, transformer)
    assert out is not None
    decorator = out.decorators[0]
    param_str = decorator.decorator.args[0].value
    assert isinstance(param_str, cst.SimpleString)
    assert param_str.value == '"left,right"'
    data_list = decorator.decorator.args[1].value
    assert isinstance(data_list, cst.List)
    tuple_values = [element.value for element in data_list.elements]
    assert all(isinstance(value, cst.Tuple) for value in tuple_values)
    method_param = next(p for p in out.params.params if isinstance(p.name, cst.Name) and p.name.value == "left")
    assert _annotation_code(method_param) == "str"
    status_param = next(p for p in out.params.params if isinstance(p.name, cst.Name) and p.name.value == "right")
    assert _annotation_code(status_param) == "int"


def test_convert_simple_subtests_enumerate_name_reference():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    cases_assignment = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("cases"))],
                value=cst.List(
                    [
                        cst.Element(
                            value=cst.Dict(
                                elements=[
                                    cst.DictElement(
                                        key=cst.SimpleString('"email"'), value=cst.SimpleString('"alpha@example.com"')
                                    ),
                                    cst.DictElement(key=cst.SimpleString('"active"'), value=cst.Name("True")),
                                ]
                            )
                        ),
                        cst.Element(
                            value=cst.Dict(
                                elements=[
                                    cst.DictElement(
                                        key=cst.SimpleString('"email"'), value=cst.SimpleString('"beta@example.org"')
                                    ),
                                    cst.DictElement(key=cst.SimpleString('"active"'), value=cst.Name("False")),
                                ]
                            )
                        ),
                    ]
                ),
            )
        ]
    )
    iter_call = cst.Call(func=cst.Name("enumerate"), args=[cst.Arg(value=cst.Name("cases"))])
    loop_target = cst.Tuple(
        [cst.Element(value=cst.Name("index")), cst.Element(value=cst.Name("case"))]
    )
    sub_call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")),
        args=[
            cst.Arg(keyword=cst.Name("index"), value=cst.Name("index")),
            cst.Arg(keyword=cst.Name("case"), value=cst.Name("case")),
        ],
    )
    with_node = cst.With(
        items=[cst.WithItem(item=sub_call)],
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("case"))])]),
    )
    loop = cst.For(target=loop_target, iter=iter_call, body=cst.IndentedBlock(body=[with_node]))
    func = cst.FunctionDef(
        name=cst.Name("test_cases"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=[cases_assignment, loop]),
    )

    out = st.convert_simple_subtests_to_parametrize(func, func, transformer)
    assert out is not None
    decorator = out.decorators[0]
    param_arg = decorator.decorator.args[0].value
    assert isinstance(param_arg, cst.SimpleString)
    assert param_arg.value == '"index,case"'
    data_arg = decorator.decorator.args[1].value
    assert isinstance(data_arg, cst.List)
    assert len(data_arg.elements) == 2
    first_tuple = data_arg.elements[0].value
    assert isinstance(first_tuple, cst.Tuple)
    first_index = first_tuple.elements[0].value
    assert isinstance(first_index, cst.Integer)
    assert first_index.value == "0"
    first_case = first_tuple.elements[1].value
    assert isinstance(first_case, cst.Dict)

    assert all(
        not (
            isinstance(stmt, cst.SimpleStatementLine)
            and any(
                isinstance(small, cst.Assign)
                and isinstance(small.targets[0].target, cst.Name)
                and small.targets[0].target.value == "cases"
                for small in stmt.body
            )
        )
        for stmt in out.body.body
    )

    index_param = next(p for p in out.params.params if isinstance(p.name, cst.Name) and p.name.value == "index")
    assert _annotation_code(index_param) == "int"
    case_param = next(p for p in out.params.params if isinstance(p.name, cst.Name) and p.name.value == "case")
    assert _annotation_code(case_param) == "dict[str, object]"


def test_convert_simple_subtests_dict_items():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    operations_assignment = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("operations"))],
                value=cst.Dict(
                    elements=[
                        cst.DictElement(
                            key=cst.SimpleString('"add"'),
                            value=cst.Tuple(
                                [
                                    cst.Element(value=cst.Name("add_fn")),
                                    cst.Element(
                                        value=cst.List(
                                            [
                                                cst.Element(
                                                    value=cst.Tuple(
                                                        [
                                                            cst.Element(value=cst.Integer("1")),
                                                            cst.Element(value=cst.Integer("2")),
                                                            cst.Element(value=cst.Integer("3")),
                                                        ]
                                                    )
                                                ),
                                                cst.Element(
                                                    value=cst.Tuple(
                                                        [
                                                            cst.Element(value=cst.Integer("2")),
                                                            cst.Element(value=cst.Integer("3")),
                                                            cst.Element(value=cst.Integer("5")),
                                                        ]
                                                    )
                                                ),
                                            ]
                                        )
                                    ),
                                ]
                            ),
                        ),
                        cst.DictElement(
                            key=cst.SimpleString('"multiply"'),
                            value=cst.Tuple(
                                [
                                    cst.Element(value=cst.Name("mul_fn")),
                                    cst.Element(
                                        value=cst.List(
                                            [
                                                cst.Element(
                                                    value=cst.Tuple(
                                                        [
                                                            cst.Element(value=cst.Integer("2")),
                                                            cst.Element(value=cst.Integer("4")),
                                                            cst.Element(value=cst.Integer("8")),
                                                        ]
                                                    )
                                                )
                                            ]
                                        )
                                    ),
                                ]
                            ),
                        ),
                    ]
                ),
            )
        ]
    )
    iter_items = cst.Call(
        func=cst.Attribute(value=cst.Name("operations"), attr=cst.Name("items")),
        args=[],
    )
    loop_target = cst.Tuple(
        [cst.Element(value=cst.Name("op_name")), cst.Element(value=cst.Name("payload"))]
    )
    sub_call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")),
        args=[cst.Arg(keyword=cst.Name("operation"), value=cst.Name("op_name"))],
    )
    with_node = cst.With(
        items=[cst.WithItem(item=sub_call)],
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("payload"))])]),
    )
    loop = cst.For(target=loop_target, iter=iter_items, body=cst.IndentedBlock(body=[with_node]))
    func = cst.FunctionDef(
        name=cst.Name("test_operations"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=[operations_assignment, loop]),
    )

    out = st.convert_simple_subtests_to_parametrize(func, func, transformer)
    assert out is not None

    decorator = out.decorators[0]
    param_arg = decorator.decorator.args[0].value
    assert isinstance(param_arg, cst.SimpleString)
    assert param_arg.value == '"op_name,payload"'
    data_arg = decorator.decorator.args[1].value
    assert isinstance(data_arg, cst.List)
    assert len(data_arg.elements) == 2
    first_tuple = data_arg.elements[0].value
    assert isinstance(first_tuple, cst.Tuple)
    assert isinstance(first_tuple.elements[0].value, cst.SimpleString)
    assert isinstance(first_tuple.elements[1].value, cst.Tuple)

    assert all(
        not (
            isinstance(stmt, cst.SimpleStatementLine)
            and any(
                isinstance(small, cst.Assign)
                and isinstance(small.targets[0].target, cst.Name)
                and small.targets[0].target.value == "operations"
                for small in stmt.body
            )
        )
        for stmt in out.body.body
    )

    op_param = next(p for p in out.params.params if isinstance(p.name, cst.Name) and p.name.value == "op_name")
    assert _annotation_code(op_param) == "str"
    payload_param = next(
        p for p in out.params.params if isinstance(p.name, cst.Name) and p.name.value == "payload"
    )
    assert payload_param.annotation is None


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
