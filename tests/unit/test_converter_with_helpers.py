import libcst as cst

from splurge_unittest_to_pytest.converter import with_helpers


def run_with(src: str):
    module = cst.parse_module(src)
    # assume single with statement in module body
    node = module.body[0]
    return with_helpers.convert_assert_raises_with(node)


def test_convert_self_assert_raises_to_pytest_raises():
    src = "with self.assertRaises(ValueError):\n    f()\n"
    new_with, needs_pytest = run_with(src)
    assert needs_pytest is True
    assert new_with is not None
    assert "pytest.raises" in cst.Module(body=[new_with]).code


def test_convert_bare_assert_raises_regex_to_pytest():
    src = "with assertRaisesRegex(ValueError, 'msg'):\n    f()\n"
    new_with, needs_pytest = run_with(src)
    assert needs_pytest is True
    assert new_with is not None
    # match token may be used; ensure pytest.raises introduced
    assert "pytest.raises" in cst.Module(body=[new_with]).code


def test_non_matching_with_returns_none():
    # with that doesn't call a Call item, or different function should return None
    src = "with open('x') as f:\n    pass\n"
    new_with, needs_pytest = run_with(src)
    assert new_with is None and needs_pytest is False
