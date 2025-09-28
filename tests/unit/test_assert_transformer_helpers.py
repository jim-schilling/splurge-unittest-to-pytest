import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    _build_with_item_from_assert_call,
    _create_with_wrapping_next_stmt,
    _get_self_attr_call,
)


def parse_stmt(code: str) -> cst.BaseStatement:
    module = cst.parse_module(code)
    return module.body[0]


def test_get_self_attr_call_matches():
    stmt = parse_stmt("self.assertLogs('x')")
    res = _get_self_attr_call(stmt)
    assert res is not None
    name, call = res
    assert name == "assertLogs"
    assert isinstance(call, cst.Call)


def test_get_self_attr_call_none_for_non_expr():
    stmt = parse_stmt("x = 1")
    res = _get_self_attr_call(stmt)
    assert res is None


def test_build_with_item_warns_and_match():
    stmt = parse_stmt("self.assertWarns(Exception, match='x')")
    res = _get_self_attr_call(stmt)
    assert res is not None
    _, call = res
    wi = _build_with_item_from_assert_call(call)
    assert wi is not None
    # expect pytest.warns in the WithItem
    assert isinstance(wi.item, cst.Call)
    func = wi.item.func
    assert isinstance(func, cst.Attribute)
    assert func.attr.value == "warns"


def test_build_with_item_assertlogs_default_level():
    stmt = parse_stmt("self.assertLogs('logger')")
    res = _get_self_attr_call(stmt)
    assert res is not None
    _, call = res
    wi = _build_with_item_from_assert_call(call)
    assert wi is not None
    assert isinstance(wi.item, cst.Call)
    func = wi.item.func
    assert isinstance(func, cst.Attribute)
    assert func.attr.value == "at_level"


def test_create_with_wrapping_next_stmt_unwraps_and_pass():
    # when next_stmt is a normal statement
    wi = cst.WithItem(item=cst.Call(func=cst.Attribute(value=cst.Name(value="caplog"), attr=cst.Name(value="at_level")), args=[]))
    stmt = parse_stmt("x = 1")
    wnode, consumed = _create_with_wrapping_next_stmt(wi, stmt)
    assert consumed == 2
    assert isinstance(wnode, cst.With)

    # when next_stmt is None -> pass body
    wnode2, consumed2 = _create_with_wrapping_next_stmt(wi, None)
    assert consumed2 == 1
    assert isinstance(wnode2, cst.With)
