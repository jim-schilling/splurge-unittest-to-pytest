import libcst as cst
from libcst import matchers as m

from splurge_unittest_to_pytest.stages import assertion_rewriter


def _run_src(src: str):
    mod = cst.parse_module(src)
    return assertion_rewriter.assertion_rewriter_stage({"module": mod})


def _mod_from_call(call_src: str):
    src = f"def test():\n    {call_src}\n"
    return _run_src(src)["module"]


def test_basic_comparisons_map():
    mapping = [
        ("self.assertEqual(a, b)", cst.Equal),
        ("self.assertNotEqual(a, b)", cst.NotEqual),
        ("self.assertIn(x, y)", cst.In),
        ("self.assertNotIn(x, y)", cst.NotIn),
        ("self.assertIs(a, b)", cst.Is),
        ("self.assertIsNot(a, b)", cst.IsNot),
        ("self.assertGreater(a, b)", cst.GreaterThan),
        ("self.assertGreaterEqual(a, b)", cst.GreaterThanEqual),
        ("self.assertLess(a, b)", cst.LessThan),
        ("self.assertLessEqual(a, b)", cst.LessThanEqual),
        ("self.assertListEqual(a, b)", cst.Equal),
        ("self.assertDictEqual(a, b)", cst.Equal),
        ("self.assertMultiLineEqual(a, b)", cst.Equal),
    ]

    for call_src, expected_op in mapping:
        mod = _mod_from_call(call_src)
        found = False
        for comp in cst.matchers.findall(mod, m.Comparison()):
            for ct in comp.comparisons:
                if isinstance(ct.operator, expected_op):
                    found = True
                    break
            if found:
                break
        assert found, f"Expected operator {expected_op} for {call_src}"


def test_identity_and_membership():
    src = """
def test():
    self.assertIsNotNone(x)
    self.assertNotIsInstance(x, int)
"""
    res = _run_src(src)
    mod = res["module"]
    # assertIsNotNone -> Comparison with IsNot
    has_isnot = any(
        isinstance(ct.operator, cst.IsNot) for c in cst.matchers.findall(mod, m.Comparison()) for ct in c.comparisons
    )
    assert has_isnot

    # assertNotIsInstance -> UnaryOperation of Not wrapping isinstance call
    found_not_isinstance = False
    for un in cst.matchers.findall(mod, m.UnaryOperation()):
        inner = getattr(un, "expression", None)
        if isinstance(inner, cst.Call) and isinstance(inner.func, cst.Name) and inner.func.value == "isinstance":
            found_not_isinstance = True
            break
    assert found_not_isinstance


def test_assert_is_instance_and_not_is_instance():
    mod = _mod_from_call("self.assertIsInstance(obj, T)")
    calls = list(cst.matchers.findall(mod, m.Call()))
    assert any(isinstance(c.func, cst.Name) and c.func.value == "isinstance" for c in calls)


def test_assert_almost_equal_variants():
    # default -> pytest.approx and sets needs_pytest_import
    res = _run_src("def test():\n    self.assertAlmostEqual(a, b)\n")
    code = res["module"].code
    assert "pytest.approx" in code
    assert res.get("needs_pytest_import", False) is True

    # delta -> abs(...) <= delta
    res2 = _run_src("def test():\n    self.assertAlmostEqual(a, b, delta=0.1)\n")
    assert "abs(" in res2["module"].code or "<=" in res2["module"].code

    # places positional numeric -> round(...)
    res3 = _run_src("def test():\n    self.assertAlmostEqual(a, b, 3)\n")
    assert "round(" in res3["module"].code


def test_assert_not_almost_equal_variants():
    # delta -> abs(...) > delta (GreaterThan)
    res = _run_src("def test():\n    self.assertNotAlmostEqual(a, b, delta=0.5)\n")
    mod = res["module"]
    found_gt = any(
        isinstance(ct.operator, cst.GreaterThan)
        for c in cst.matchers.findall(mod, m.Comparison())
        for ct in c.comparisons
    )
    assert found_gt

    # places positional numeric -> round(...) != 0 or a not-round unary form
    res2 = _run_src("def test():\n    self.assertNotAlmostEqual(a, b, 2)\n")
    assert "round(" in res2["module"].code


def test_assert_raises_callable_and_context():
    src = """
def test():
    self.assertRaises(ValueError, int, 'x')
    with self.assertRaises(ValueError):
        raise ValueError()
"""
    res = _run_src(src)
    mod = res["module"]
    # ensure pytest.raises appears for with-form
    assert "pytest.raises" in mod.code
    # callable form should still exist as call to assertRaises (conservative)
    assert "assertRaises(" in mod.code
