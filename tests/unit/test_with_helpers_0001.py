from __future__ import annotations

import libcst as cst
from libcst import matchers as m
from splurge_unittest_to_pytest.converter.with_helpers import convert_assert_raises_with


def _with_from_src(src: str) -> cst.With:
    mod = cst.parse_module(src)
    matches = m.findall(mod, m.With())
    if matches:
        return matches[0]
    raise AssertionError("no With node found")


def test_convert_self_assert_raises() -> None:
    src = """
class T:
    def test(self):
        with self.assertRaises(ValueError):
            x = 1
"""
    w = _with_from_src(src)
    new_w, needs = convert_assert_raises_with(w)
    assert needs is True
    assert new_w is not None
    # Should contain pytest.raises attribute in the WithItem
    item = new_w.items[0]
    assert isinstance(item.item, cst.Call)
    func = item.item.func
    assert isinstance(func, cst.Attribute)
    assert getattr(func.value, "value", None) == "pytest"


def test_convert_bare_assert_raises_name() -> None:
    src = """
def f():
    with assertRaises(KeyError):
        pass
"""
    w = _with_from_src(src)
    new_w, needs = convert_assert_raises_with(w)
    assert needs is True
    assert new_w is not None


def test_non_matching_with_returns_none() -> None:
    src = """
with open('x') as fh:
    data = fh.read()
"""
    w = _with_from_src(src)
    new_w, needs = convert_assert_raises_with(w)
    assert needs is False
    assert new_w is None
