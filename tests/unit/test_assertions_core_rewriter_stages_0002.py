import libcst as cst
from libcst import matchers as m

from splurge_unittest_to_pytest.stages import assertion_rewriter


def _run(src: str):
    module = cst.parse_module(src)
    return assertion_rewriter.assertion_rewriter_stage({"module": module})


def test_bare_name_assert_equal_conversion():
    # ensure bare function name (no `self.`) is also converted
    src = """
def test():
    assertEqual(a, b)
"""
    res = _run(src)
    code = res["module"].code
    assert "assert a ==" in code


def test_assert_is_none_string_literal_guard_returns_none():
    # string literal should be treated like a literal and not produce `is None`
    src = """
def test():
    self.assertIsNone('x')
"""
    res = _run(src)
    code = res["module"].code
    assert "is None" not in code


def test_assert_raises_regex_without_match_arg_fallback():
    # ensure assertRaisesRegex with a single arg falls back to pytest.raises without match kw
    src = """
def test():
    with self.assertRaisesRegex(ValueError):
        raise ValueError()
"""
    res = _run(src)
    code = res["module"].code
    assert "pytest.raises(ValueError" in code
    # when only a single arg present, we should not inject a match= keyword
    assert "match" not in code


def test_assert_not_almost_equal_with_delta_produces_greater_than():
    src = """
def test():
    self.assertNotAlmostEqual(a, b, delta=0.5)
"""
    res = _run(src)
    mod = res["module"]
    # find any Comparison node that uses GreaterThan operator
    found_gt = False
    for comp in cst.matchers.findall(mod, m.Comparison()):
        for ct in comp.comparisons:
            if isinstance(ct.operator, cst.GreaterThan):
                found_gt = True
                break
        if found_gt:
            break
    assert found_gt is True


def test_assert_is_instance_emits_isinstance_call():
    src = """
def test():
    self.assertIsInstance(obj, Type)
"""
    res = _run(src)
    mod = res["module"]
    # Look for a Call whose func is Name('isinstance')
    calls = list(cst.matchers.findall(mod, m.Call()))
    assert any(isinstance(c.func, cst.Name) and c.func.value == "isinstance" for c in calls)
