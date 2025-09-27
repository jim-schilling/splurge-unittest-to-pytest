import types

import libcst as cst

from splurge_unittest_to_pytest.transformers import subtest_transformer as st


def _empty_func():
    return cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[]))


def test_empty_body_returns_none():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    f = _empty_func()
    out = st.convert_simple_subtests_to_parametrize(f, f, transformer)
    assert out is None


def test_first_not_for_returns_none():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # Build a function where first stmt is not For (e.g., Expr)
    expr = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("x"))])
    f = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[expr]))
    out = st.convert_simple_subtests_to_parametrize(f, f, transformer)
    assert out is None


def test_for_with_non_single_with_returns_none():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # For body with two statements
    inner = cst.IndentedBlock(
        body=[
            cst.SimpleStatementLine(body=[cst.Expr(cst.Name("x"))]),
            cst.SimpleStatementLine(body=[cst.Expr(cst.Name("y"))]),
        ]
    )
    for_node = cst.For(target=cst.Name("i"), iter=cst.List([cst.Element(cst.Integer("1"))]), body=inner)
    f = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[for_node]))
    out = st.convert_simple_subtests_to_parametrize(f, f, transformer)
    assert out is None


def test_with_not_subtest_returns_none():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # With has call but not self.subTest
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("other"), attr=cst.Name("subTest")), args=[cst.Arg(value=cst.Name("i"))]
    )
    with_node = cst.With(
        items=[cst.WithItem(item=call)],
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("x"))])]),
    )
    for_node = cst.For(
        target=cst.Name("i"), iter=cst.List([cst.Element(cst.Integer("1"))]), body=cst.IndentedBlock(body=[with_node])
    )
    f = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[for_node]))
    out = st.convert_simple_subtests_to_parametrize(f, f, transformer)
    assert out is None


def test_subtest_with_multiple_args_returns_none():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")),
        args=[cst.Arg(value=cst.Name("i")), cst.Arg(value=cst.Name("j"))],
    )
    with_node = cst.With(
        items=[cst.WithItem(item=call)],
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("x"))])]),
    )
    for_node = cst.For(
        target=cst.Name("i"), iter=cst.List([cst.Element(cst.Integer("1"))]), body=cst.IndentedBlock(body=[with_node])
    )
    f = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[for_node]))
    out = st.convert_simple_subtests_to_parametrize(f, f, transformer)
    assert out is None


def test_iter_unknown_type_returns_none():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # iter is a Call to unknown function foo(), not range or list/tuple or Name
    iter_node = cst.Call(func=cst.Name("foo"), args=[])
    # build inner With node
    inner_call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")), args=[cst.Arg(value=cst.Name("i"))]
    )
    with_item = cst.WithItem(item=inner_call)
    inner_with = cst.With(
        items=[with_item], body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("x"))])])
    )
    for_node = cst.For(target=cst.Name("i"), iter=iter_node, body=cst.IndentedBlock(body=[inner_with]))
    f = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[for_node]))
    out = st.convert_simple_subtests_to_parametrize(f, f, transformer)
    assert out is None


def test_range_with_non_integer_arg_returns_none():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    iter_node = cst.Call(func=cst.Name("range"), args=[cst.Arg(value=cst.SimpleString("'x'"))])
    inner_call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")), args=[cst.Arg(value=cst.Name("i"))]
    )
    with_item = cst.WithItem(item=inner_call)
    inner_with = cst.With(
        items=[with_item], body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("x"))])])
    )
    for_node = cst.For(target=cst.Name("i"), iter=iter_node, body=cst.IndentedBlock(body=[inner_with]))
    f = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[for_node]))
    out = st.convert_simple_subtests_to_parametrize(f, f, transformer)
    assert out is None


def test_loop_target_mismatch_returns_none():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # subTest(k) but loop target is i
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")), args=[cst.Arg(value=cst.Name("k"))]
    )
    with_node = cst.With(
        items=[cst.WithItem(item=call)],
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("x"))])]),
    )
    for_node = cst.For(
        target=cst.Name("i"), iter=cst.List([cst.Element(cst.Integer("1"))]), body=cst.IndentedBlock(body=[with_node])
    )
    f = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[for_node]))
    out = st.convert_simple_subtests_to_parametrize(f, f, transformer)
    assert out is None


def test_existing_parametrize_detection_by_name():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # decorator that is a bare name 'parametrize'
    existing_deco = cst.Decorator(decorator=cst.Call(func=cst.Name("parametrize")))
    inner_call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")), args=[cst.Arg(value=cst.Name("i"))]
    )
    with_item = cst.WithItem(item=inner_call)
    inner_with = cst.With(
        items=[with_item], body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("x"))])])
    )
    for_node = cst.For(
        target=cst.Name("i"), iter=cst.List([cst.Element(cst.Integer("1"))]), body=cst.IndentedBlock(body=[inner_with])
    )
    func = _empty_func().with_changes(body=cst.IndentedBlock(body=[for_node]), decorators=[existing_deco])
    out = st.convert_simple_subtests_to_parametrize(func, func, transformer)
    assert out is None


def test_non_name_keyword_in_subtest_returns_none():
    transformer = types.SimpleNamespace(needs_pytest_import=False)
    # keyword that is not a Name
    kw = cst.Arg(keyword=cst.Attribute(value=cst.Name("a"), attr=cst.Name("b")), value=cst.Name("i"))
    call = cst.Call(func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("subTest")), args=[kw])
    with_node = cst.With(
        items=[cst.WithItem(item=call)],
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(cst.Name("x"))])]),
    )
    for_node = cst.For(
        target=cst.Name("i"), iter=cst.List([cst.Element(cst.Integer("1"))]), body=cst.IndentedBlock(body=[with_node])
    )
    f = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=[for_node]))
    out = st.convert_simple_subtests_to_parametrize(f, f, transformer)
    assert out is None
