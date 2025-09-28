import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    get_caplog_level_args,
    transform_with_items,
)


def test_transform_with_items_uses_default_info_for_caplog():
    module = cst.parse_module(
        """
with self.assertLogs('x'):
    pass
"""
    )
    original_with = module.body[0]
    assert isinstance(original_with, cst.With)
    new_with, alias_name, changed = transform_with_items(original_with)
    assert changed is True
    # ensure the new With contains a caplog.at_level call with a SimpleString '"INFO"'
    item = new_with.items[0]
    assert isinstance(item.item, cst.Call)
    assert isinstance(item.item.func, cst.Attribute)
    assert item.item.func.attr.value == "at_level"
    assert len(item.item.args) == 1
    arg = item.item.args[0]
    assert isinstance(arg.value, cst.SimpleString)
    assert arg.value.value == '"INFO"'
