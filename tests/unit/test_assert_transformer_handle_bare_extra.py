import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    build_with_item_from_assert_call,
    get_caplog_level_args,
    handle_bare_assert_call,
    transform_with_items,
)


def _stmt(code: str):
    module = cst.parse_module(code)
    return module.body[0]


def test_get_caplog_level_args_defaults_to_info():
    call = cst.parse_expression("self.assertLogs('x')")
    if isinstance(call, cst.BaseExpression):
        # call is a BaseExpression wrapper; unwrap for helper
        call = call
    assert isinstance(call, cst.Call)
    args = get_caplog_level_args(call)
    assert len(args) == 1
    assert isinstance(args[0].value, cst.SimpleString)
    assert args[0].value.value == '"INFO"'


def test_pytest_raises_alias_preserved_when_existing_asname():
    # When an existing With uses `self.assertRaises(...) as cm`, transform_with_items should
    # preserve the `as` alias on the WithItem when converting to pytest.raises(...)
    module = cst.parse_module(
        """
with self.assertRaises(ValueError) as cm:
    _ = cm.exception
"""
    )
    original_with = module.body[0]
    assert isinstance(original_with, cst.With)
    new_with, alias_name, changed = transform_with_items(original_with)
    assert changed is True
    assert alias_name == "cm"
    # Ensure the new WithItem preserves the asname
    new_item = new_with.items[0]
    assert new_item.asname is not None
    assert isinstance(new_item.asname.name, cst.Name)
    assert new_item.asname.name.value == "cm"
