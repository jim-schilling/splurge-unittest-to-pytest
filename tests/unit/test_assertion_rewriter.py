import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def _run(src: str):
    module = cst.parse_module(src)
    return assertion_rewriter_stage({"module": module})


def test_property_style_assertions_attribute_equality():
    s = """
class Test:
    def test_attrs(self):
        class Obj:
            def __init__(self):
                self.count = 3
                self.name = 'foo'

        o = Obj()
        self.assertEqual(o.count, 3)
        self.assertEqual(o.name, 'foo')
"""

    res = _run(s)
    code = res["module"].code
    # expect attribute comparisons converted to pytest-style asserts
    assert "assert o.count == 3" in code
    assert "assert o.name == 'foo'" in code


def test_property_style_assertions_is_none_and_truthiness():
    s = """
class Test:
    def test_attrs(self):
        class Obj:
            def __init__(self):
                self.value = None
                self.enabled = False

        o = Obj()
        self.assertIsNone(o.value)
        self.assertTrue(o.enabled is False)
        self.assertFalse(o.enabled)
"""

    res = _run(s)
    code = res["module"].code
    assert "assert o.value is None" in code
    # both forms should be converted sensibly
    assert "assert o.enabled is False" in code or "assert not o.enabled" in code


def test_property_style_membership_and_identity():
    s = """
class Test:
    def test_attrs(self):
        class Obj:
            def __init__(self):
                self.items = [1, 2, 3]
                self.ref = self

        o = Obj()
        self.assertIn(2, o.items)
        self.assertIs(o.ref, o)
"""

    res = _run(s)
    code = res["module"].code
    assert "assert 2 in o.items" in code
    assert "assert o.ref is o" in code


def test_assert_equal_basic_and_msg_stripped():
    src = "self.assertEqual(a, b, 'msg')\n"
    res = _run(src)
    code = res["module"].code
    assert "assert a == b" in code
    assert "msg" not in code


def test_assert_is_none_literal_skipped_and_var_converted():
    # literal -> skipped (left as-is)
    res_lit = _run("self.assertIsNone(1)\n")
    assert "self.assertIsNone(1)" in res_lit["module"].code

    # variable -> converted to 'is None'
    res_var = _run("self.assertIsNone(foo)\n")
    assert "assert foo is None" in res_var["module"].code


def test_assert_almost_equal_delta_and_places_and_default():
    # delta kw -> abs(a - b) <= delta
    res_delta = _run("self.assertAlmostEqual(a, b, delta=0.1)\n")
    assert "abs(a - b)" in res_delta["module"].code
    assert "<= 0.1" in res_delta["module"].code

    # numeric third positional -> treated as places -> round(..., places) == 0
    res_places = _run("self.assertAlmostEqual(a, b, 2)\n")
    assert "round(a - b, 2)" in res_places["module"].code

    # default -> uses pytest.approx and sets flag
    res_default = _run("self.assertAlmostEqual(a, b)\n")
    assert "pytest.approx" in res_default["module"].code
    assert res_default.get("needs_pytest_import") is True


def test_assert_not_almost_equal_delta_and_default():
    res_delta = _run("self.assertNotAlmostEqual(a, b, delta=0.2)\n")
    assert "abs(a - b)" in res_delta["module"].code
    assert "> 0.2" in res_delta["module"].code

    res_default = _run("self.assertNotAlmostEqual(a, b)\n")
    assert "pytest.approx" in res_default["module"].code
    assert res_default.get("needs_pytest_import") is True


def test_assert_raises_and_raises_regex_converted():
    src = "with self.assertRaises(ValueError):\n    raise ValueError()\n"
    res = _run(src)
    code = res["module"].code
    assert "with pytest.raises(ValueError)" in code
    assert res.get("needs_pytest_import") is True

    src_regex = "with self.assertRaisesRegex(ValueError, 'bad'):\n    raise ValueError()\n"
    res_regex = _run(src_regex)
    code = res_regex["module"].code
    # allow for formatting differences around '=' (match = 'bad')
    assert "with pytest.raises(ValueError" in code
    assert "match" in code and "'bad'" in code


def test_assert_regex_sets_re_import():
    res = _run("self.assertRegex(text, pattern)\n")
    code = res["module"].code
    assert "re.search(" in code
    assert res.get("needs_re_import") is True


def test_basic_boolean_and_membership_and_identity_and_instance():
    res = _run("self.assertTrue(flag)\nself.assertFalse(flag)\nself.assertIn(x, y)\nself.assertNotIn(x, y)\nself.assertIs(a, b)\nself.assertIsNot(a, b)\nself.assertIsInstance(o, T)\nself.assertNotIsInstance(o, T)\n")
    code = res["module"].code
    # boolean
    assert "assert flag" in code
    assert "not flag" in code or "assert not flag" in code
    # membership
    assert "in y" in code
    assert "not in y" in code
    # identity
    assert "is b" in code
    assert "is not b" in code
    # isinstance
    assert "isinstance(o, T)" in code
    assert "not isinstance(o, T)" in code


def test_aliases_and_collections_and_multi_line_equal():
    # aliases: assertEquals -> assertEqual
    res = _run("self.assertEquals(x, y)\n")
    assert "assert x == y" in res["module"].code

    # collection equality variants map to equality
    res_col = _run("self.assertListEqual(a, b)\nself.assertDictEqual(a, b)\nself.assertSetEqual(a, b)\n")
    ccode = res_col["module"].code
    assert "a == b" in ccode

    # multi-line equal maps to equality too
    res_multi = _run("self.assertMultiLineEqual(s1, s2)\n")
    assert "s1 == s2" in res_multi["module"].code


def test_assert_almost_equal_non_numeric_third_positional_is_msg():
    # third positional is not numeric -> treated as msg and dropped
    res = _run("self.assertAlmostEqual(a, b, 'not-a-number')\n")
    code = res["module"].code
    # should fallback to pytest.approx default since third positional was dropped
    assert "pytest.approx" in code


def test_assert_is_none_with_simple_string_literal_skipped():
    # string literal should be considered a literal and cause skip
    res = _run("self.assertIsNone('x')\n")
    assert "self.assertIsNone('x')" in res["module"].code


def test_assert_raises_standalone_name_and_non_self_calls():
    # If assertRaises is called as a bare name (not self.assertRaises) it's treated similarly
    res = _run("with assertRaises(ValueError):\n    raise ValueError()\n")
    # fallback: code likely unchanged (conservative) but ensure function returns a module
    assert "with assertRaises" in res["module"].code or "with pytest.raises" in res["module"].code
