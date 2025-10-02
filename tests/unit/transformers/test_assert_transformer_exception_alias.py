import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_transformer


def _module_from_with(alias_name: str) -> cst.Module:
    # Construct a with self.assertRaises(ValueError) as <alias>:
    #     assert str(<alias>.exception) == 'Cannot divide by zero'
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertRaises")),
            args=[cst.Arg(value=cst.Name(value="ValueError"))],
        ),
        asname=cst.AsName(name=cst.Name(value=alias_name)),
    )
    assert_stmt = cst.Assert(
        test=cst.Comparison(
            left=cst.Call(
                func=cst.Name(value="str"),
                args=[cst.Arg(value=cst.Attribute(value=cst.Name(value=alias_name), attr=cst.Name(value="exception")))],
            ),
            comparisons=[
                cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.SimpleString(value="'Cannot divide by zero'"))
            ],
        )
    )
    with_node = cst.With(body=cst.IndentedBlock(body=[assert_stmt]), items=[with_item])
    mod = cst.Module(body=[with_node])
    return mod


def test_exception_alias_rewritten_to_value():
    mod = _module_from_with("context")

    # First transform With.items from self.assertRaises -> pytest.raises
    new_with, alias_name, changed = assert_transformer.transform_with_items(mod.body[0])
    assert changed is True
    assert alias_name == "context"

    # Now rewrite asserts inside the with body to use alias.value semantics
    rewritten = assert_transformer.rewrite_asserts_using_alias_in_with_body(new_with, alias_name)

    # Build a temporary module to render the With node to source code
    code = cst.Module(body=[rewritten]).code
    # The rewritten assertion should reference 'context.value' instead of 'context.exception'
    assert "context.value" in code
    assert "context.exception" not in code


def test_repr_wrapper_rewritten_to_value():
    # with self.assertRaises(ValueError) as context:
    #     assert repr(context.exception) == 'Cannot divide by zero'
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertRaises")),
            args=[cst.Arg(value=cst.Name(value="ValueError"))],
        ),
        asname=cst.AsName(name=cst.Name(value="context")),
    )
    call_expr = cst.Call(
        func=cst.Name(value="repr"),
        args=[cst.Arg(value=cst.Attribute(value=cst.Name(value="context"), attr=cst.Name(value="exception")))],
    )
    assert_stmt = cst.Assert(
        test=cst.Comparison(
            left=call_expr,
            comparisons=[
                cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.SimpleString(value="'Cannot divide by zero'"))
            ],
        )
    )
    with_node = cst.With(body=cst.IndentedBlock(body=[assert_stmt]), items=[with_item])
    mod = cst.Module(body=[with_node])

    new_with, alias_name, changed = assert_transformer.transform_with_items(mod.body[0])
    assert changed is True
    assert alias_name == "context"

    rewritten = assert_transformer.rewrite_asserts_using_alias_in_with_body(new_with, alias_name)
    code = cst.Module(body=[rewritten]).code
    assert "context.value" in code
    assert "context.exception" not in code


def test_call_with_additional_args_rewritten():
    # with self.assertRaises(ValueError) as context:
    #     assert custom(context.exception, 1) == 'Cannot divide by zero'
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertRaises")),
            args=[cst.Arg(value=cst.Name(value="ValueError"))],
        ),
        asname=cst.AsName(name=cst.Name(value="context")),
    )
    call_expr = cst.Call(
        func=cst.Name(value="custom"),
        args=[
            cst.Arg(value=cst.Attribute(value=cst.Name(value="context"), attr=cst.Name(value="exception"))),
            cst.Arg(value=cst.Integer(value="1")),
        ],
    )
    assert_stmt = cst.Assert(
        test=cst.Comparison(
            left=call_expr,
            comparisons=[
                cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.SimpleString(value="'Cannot divide by zero'"))
            ],
        )
    )
    with_node = cst.With(body=cst.IndentedBlock(body=[assert_stmt]), items=[with_item])
    mod = cst.Module(body=[with_node])

    new_with, alias_name, changed = assert_transformer.transform_with_items(mod.body[0])
    assert changed is True
    assert alias_name == "context"

    rewritten = assert_transformer.rewrite_asserts_using_alias_in_with_body(new_with, alias_name)
    code = cst.Module(body=[rewritten]).code
    assert "context.value" in code
    assert "context.exception" not in code


def test_comparator_side_wrapper_rewritten():
    # with self.assertRaises(ValueError) as context:
    #     assert 'Cannot divide by zero' == str(context.exception)
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertRaises")),
            args=[cst.Arg(value=cst.Name(value="ValueError"))],
        ),
        asname=cst.AsName(name=cst.Name(value="context")),
    )
    call_expr = cst.Call(
        func=cst.Name(value="str"),
        args=[cst.Arg(value=cst.Attribute(value=cst.Name(value="context"), attr=cst.Name(value="exception")))],
    )
    comp = cst.Comparison(
        left=cst.SimpleString(value="'Cannot divide by zero'"),
        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=call_expr)],
    )
    assert_stmt = cst.Assert(test=comp)
    with_node = cst.With(body=cst.IndentedBlock(body=[assert_stmt]), items=[with_item])
    mod = cst.Module(body=[with_node])

    new_with, alias_name, changed = assert_transformer.transform_with_items(mod.body[0])
    assert changed is True
    assert alias_name == "context"

    rewritten = assert_transformer.rewrite_asserts_using_alias_in_with_body(new_with, alias_name)
    code = cst.Module(body=[rewritten]).code
    assert "context.value" in code
    assert "context.exception" not in code
