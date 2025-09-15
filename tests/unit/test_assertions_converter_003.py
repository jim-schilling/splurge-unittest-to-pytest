import libcst as cst

from splurge_unittest_to_pytest.converter.with_helpers import convert_assert_raises_with

DOMAINS = ["assertions", "converter"]


def _parse_with(src: str) -> cst.With:
    module = cst.parse_module(src)
    # Expect a single with statement at module.body[0]
    node = module.body[0]
    assert isinstance(node, cst.SimpleStatementLine) or isinstance(node, cst.With)
    # handle either SimpleStatementLine(with ...) or With directly
    if isinstance(node, cst.SimpleStatementLine):
        inner = node.body[0]
        assert isinstance(inner, cst.With)
        return inner
    return node


def test_convert_self_assert_raises_to_pytest():
    src = """
with self.assertRaises(ValueError):
    do_something()
"""
    w = _parse_with(src)
    new_w, needs = convert_assert_raises_with(w)
    assert needs is True
    assert new_w is not None
    # ensure the with item func is a call to pytest.raises (structural check)
    item = new_w.items[0]
    assert isinstance(item.item, cst.Call)


def test_convert_bare_assert_raises_regex_to_pytest():
    src = """
with assertRaisesRegex(MyError, r"fail"):
    do_other()
"""
    w = _parse_with(src)
    new_w, needs = convert_assert_raises_with(w)
    assert needs is True
    assert new_w is not None
    item = new_w.items[0]
    assert isinstance(item.item, cst.Call)


def test_non_assert_with_returns_none():
    src = """
with context_manager():
    pass
"""
    w = _parse_with(src)
    new_w, needs = convert_assert_raises_with(w)
    assert new_w is None
    assert needs is False
