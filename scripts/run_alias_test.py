import sys

import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_transformer


def _module_from_with(alias_name: str) -> cst.Module:
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


# Run checks similar to unit tests
try:
    mod = _module_from_with("context")
    new_with, alias_name, changed = assert_transformer.transform_with_items(mod.body[0])
    assert changed is True and alias_name == "context"
    rewritten = assert_transformer.rewrite_asserts_using_alias_in_with_body(new_with, alias_name)
    code = cst.Module(body=[rewritten]).code
    assert "context.value" in code and "context.exception" not in code

    # repr wrapper
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
    new_with, alias_name, changed = assert_transformer.transform_with_items(with_node)
    assert changed is True and alias_name == "context"
    rewritten = assert_transformer.rewrite_asserts_using_alias_in_with_body(new_with, alias_name)
    code = cst.Module(body=[rewritten]).code
    assert "context.value" in code and "context.exception" not in code

    # custom call
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
    new_with, alias_name, changed = assert_transformer.transform_with_items(with_node)
    assert changed is True and alias_name == "context"
    rewritten = assert_transformer.rewrite_asserts_using_alias_in_with_body(new_with, alias_name)
    code = cst.Module(body=[rewritten]).code
    assert "context.value" in code and "context.exception" not in code

    # comparator side
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
    new_with, alias_name, changed = assert_transformer.transform_with_items(with_node)
    assert changed is True and alias_name == "context"
    rewritten = assert_transformer.rewrite_asserts_using_alias_in_with_body(new_with, alias_name)
    code = cst.Module(body=[rewritten]).code
    assert "context.value" in code and "context.exception" not in code

    print("All alias rewrite checks passed")
    sys.exit(0)
except AssertionError:
    print("Alias rewrite check failed")
    raise
except Exception:
    print("Unexpected error during alias check")
    raise
