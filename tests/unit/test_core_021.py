import libcst as cst

from splurge_unittest_to_pytest.converter import with_helpers

DOMAINS = ["core"]


def make_with(src: str) -> cst.With:
    mod = cst.parse_module(src)
    for node in mod.body:
        if isinstance(node, cst.With):
            return node
    raise RuntimeError("no with found")


def test_convert_assert_raises_with_self_call():
    src = "with self.assertRaises(ValueError):\n    pass\n"
    w = make_with(src)
    new_w, needs = with_helpers.convert_assert_raises_with(w)
    assert needs is True
    assert new_w is not None
    assert "pytest.raises" in cst.Module(body=[new_w]).code


def test_convert_assert_raises_with_bare_call():
    src = "with assertRaises(ValueError):\n    pass\n"
    w = make_with(src)
    new_w, needs = with_helpers.convert_assert_raises_with(w)
    assert needs is True
    assert new_w is not None
    assert "pytest.raises" in cst.Module(body=[new_w]).code


def test_convert_assert_raises_regex():
    src = "with self.assertRaisesRegex(ValueError, 'bad'):\n    pass\n"
    w = make_with(src)
    new_w, needs = with_helpers.convert_assert_raises_with(w)
    assert needs is True
    assert new_w is not None
    # Inspect the inner Call for a keyword argument named 'match'
    inner_call = new_w.items[0].item
    assert any(a.keyword and a.keyword.value == "match" for a in inner_call.args)


def test_convert_assert_raises_with_non_call():
    src = "with open('x') as f:\n    pass\n"
    w = make_with(src)
    new_w, needs = with_helpers.convert_assert_raises_with(w)
    assert new_w is None and needs is False


# ...existing code above covers the important cases
