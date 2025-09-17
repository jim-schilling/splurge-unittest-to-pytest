import libcst as cst
from libcst import matchers as m
from splurge_unittest_to_pytest.stages.assertion_rewriter import AssertionRewriter, assertion_rewriter_stage
import pytest


def _apply(expr_src: str) -> str:
    mod = cst.parse_module(expr_src)
    new = mod.visit(AssertionRewriter())
    return new.code


def test_assert_equal_conversion():
    src = "x = 1\nself.assertEqual(x, 1)\n"
    out = _apply(src)
    assert "assert x == 1" in out


def test_assert_true_conversion():
    src = "self.assertTrue(flag)\n"
    out = _apply(src)
    assert "assert flag" in out


def test_with_assert_raises_converted_to_pytest():
    src = "with self.assertRaises(ValueError):\n    do_thing()\n"
    out = _apply(src)
    assert "pytest.raises" in out


def _run(src: str):
    module = cst.parse_module(src)
    return assertion_rewriter_stage({"module": module})


def test_property_style_assertions_attribute_equality():
    s = "\nclass Test:\n    def test_attrs(self):\n        class Obj:\n            def __init__(self):\n                self.count = 3\n                self.name = 'foo'\n\n        o = Obj()\n        self.assertEqual(o.count, 3)\n        self.assertEqual(o.name, 'foo')\n"
    res = _run(s)
    code = res["module"].code
    assert "assert o.count == 3" in code
    assert "assert o.name == 'foo'" in code


def test_property_style_assertions_is_none_and_truthiness():
    s = "\nclass Test:\n    def test_attrs(self):\n        class Obj:\n            def __init__(self):\n                self.value = None\n                self.enabled = False\n\n        o = Obj()\n        self.assertIsNone(o.value)\n        self.assertTrue(o.enabled is False)\n        self.assertFalse(o.enabled)\n"
    res = _run(s)
    code = res["module"].code
    assert "assert o.value is None" in code
    assert "assert o.enabled is False" in code or "assert not o.enabled" in code


def test_property_style_membership_and_identity():
    s = "\nclass Test:\n    def test_attrs(self):\n        class Obj:\n            def __init__(self):\n                self.items = [1, 2, 3]\n                self.ref = self\n\n        o = Obj()\n        self.assertIn(2, o.items)\n        self.assertIs(o.ref, o)\n"
    res = _run(s)
    code = res["module"].code
    assert "assert 2 in o.items" in code
    assert "assert o.ref is o" in code


def test_assert_almost_equal_sets_approx_flag():
    s = "\nclass Test:\n    def test_approx(self):\n        a = 1.0\n        b = 1.000001\n        self.assertAlmostEqual(a, b)\n"
    res = _run(s)
    assert res.get("needs_pytest_import", False) is True


def test_assert_regex_sets_re_import_and_uses_search():
    s = "\nclass Test:\n    def test_re(self):\n        self.assertRegex('abc', r'b')\n        self.assertNotRegex('abc', r'z')\n"
    res = _run(s)
    assert res.get("needs_re_import", False) is True
    module = res["module"]
    found_asserts: list[cst.Assert] = []

    class AVisitor(cst.CSTVisitor):
        def visit_Assert(self, node: cst.Assert) -> None:
            found_asserts.append(node)

    module.visit(AVisitor())
    found_search = any(
        (
            isinstance(a.test, cst.Call)
            and isinstance(a.test.func, cst.Attribute)
            and isinstance(a.test.func.value, cst.Name)
            and (a.test.func.value.value == "re")
            and isinstance(a.test.func.attr, cst.Name)
            and (a.test.func.attr.value == "search")
            for a in found_asserts
        )
    )
    assert found_search, "expected re.search call in converted code"


def test_assert_raises_context_and_callable_form():
    s = "\nclass Test:\n    def test_raises_ctx(self):\n        with self.assertRaises(ValueError):\n            int('x')\n\n    def test_raises_callable(self):\n        self.assertRaises(ValueError, int, 'x')\n"
    res = _run(s)
    module = res["module"]
    found_with_raises = any(
        (
            isinstance(call.func, cst.Attribute)
            and isinstance(call.func.value, cst.Name)
            and (call.func.value.value == "pytest")
            and isinstance(call.func.attr, cst.Name)
            and (call.func.attr.value == "raises")
            for call in cst.matchers.findall(module, m.Call())
        )
    )
    assert found_with_raises is True
    assert res.get("needs_pytest_import", False) is True
    found_callable = any(
        (
            isinstance(call.func, cst.Attribute)
            and isinstance(call.func.attr, cst.Name)
            and (call.func.attr.value == "assertRaises")
            for call in cst.matchers.findall(module, m.Call())
        )
    )
    assert found_callable is True


def test_identity_and_membership_operators():
    s = "\nclass Test:\n    def test_ops(self):\n        a = object()\n        b = a\n        items = [1,2]\n        self.assertIs(a, b)\n        self.assertIsNot(a, None)\n        self.assertIn(2, items)\n        self.assertNotIn(3, items)\n"
    res = _run(s)
    module = res["module"]
    found_is = found_isnot = found_in = found_notin = False
    for node in cst.matchers.findall(module, m.Comparison()):
        for comp in node.comparisons:
            op = comp.operator
            if isinstance(op, cst.Is):
                found_is = True
            if isinstance(op, cst.IsNot):
                found_isnot = True
            if isinstance(op, cst.In):
                found_in = True
            if isinstance(op, cst.NotIn):
                found_notin = True
    assert found_is and found_isnot and found_in and found_notin


def test_truthiness_assertions():
    s = "\nclass Test:\n    def test_truth(self):\n        x = None\n        self.assertTrue(x is None)\n        self.assertFalse(x)\n"
    res = _run(s)
    module = res["module"]
    found_asserts: list[cst.Assert] = []

    class AVisitor2(cst.CSTVisitor):
        def visit_Assert(self, node: cst.Assert) -> None:
            found_asserts.append(node)

    module.visit(AVisitor2())
    assert len(found_asserts) >= 2


def test_assert_equal_basic_and_msg_stripped():
    src = "self.assertEqual(a, b, 'msg')\n"
    res = _run(src)
    code = res["module"].code
    assert "assert a == b" in code
    assert "msg" not in code


def test_assert_almost_equal_places_kw_and_not_almost_numeric_positional():
    res_places_kw = _run("self.assertAlmostEqual(a, b, places=3)\n")
    assert "round(a - b, 3)" in res_places_kw["module"].code
    res_not_places = _run("self.assertNotAlmostEqual(a, b, 2)\n")
    has_not_round = any(
        (
            isinstance(node, cst.UnaryOperation) and isinstance(node.expression, cst.Comparison)
            for node in cst.matchers.findall(res_not_places["module"], m.UnaryOperation())
        )
    )
    has_not_equal_round = any(
        (
            isinstance(node, cst.Comparison)
            and any((isinstance(comp.operator, cst.NotEqual) for comp in node.comparisons))
            for node in cst.matchers.findall(res_not_places["module"], m.Comparison())
        )
    )
    assert has_not_round or has_not_equal_round


def test_assert_not_regex_structural_not_search():
    res = _run("self.assertNotRegex(text, pattern)\n")
    module = res["module"]
    found_form = False
    for un in cst.matchers.findall(module, m.UnaryOperation()):
        inner = getattr(un, "expression", None)
        if (
            isinstance(inner, cst.Call)
            and isinstance(inner.func, cst.Attribute)
            and isinstance(inner.func.value, cst.Name)
            and (inner.func.value.value == "re")
            and isinstance(inner.func.attr, cst.Name)
            and (inner.func.attr.value == "search")
        ):
            found_form = True
            break
    if not found_form:
        for comp in cst.matchers.findall(module, m.Comparison()):
            for ct in comp.comparisons:
                if (
                    isinstance(ct.operator, cst.Is)
                    and isinstance(ct.comparator, cst.Name)
                    and (ct.comparator.value == "None")
                ):
                    if (
                        isinstance(comp.left, cst.Call)
                        and isinstance(comp.left.func, cst.Attribute)
                        and isinstance(comp.left.func.value, cst.Name)
                        and (comp.left.func.value.value == "re")
                        and isinstance(comp.left.func.attr, cst.Name)
                        and (comp.left.func.attr.value == "search")
                    ):
                        found_form = True
                        break
            if found_form:
                break
    assert found_form is True


def test_assert_is_not_none_and_not_equal_and_not_is_instance():
    s = "\nclass Test:\n    def test_ops(self):\n        a = None\n        b = 1\n        self.assertIsNotNone(a)\n        self.assertNotEqual(a, b)\n        self.assertNotIsInstance(a, int)\n"
    res = _run(s)
    module = res["module"]
    has_is_not_none = any(
        (
            isinstance(c, cst.Comparison) and any((isinstance(op.operator, cst.IsNot) for op in c.comparisons))
            for c in cst.matchers.findall(module, m.Comparison())
        )
    )
    assert has_is_not_none
    has_not_equal = any(
        (
            isinstance(c, cst.Comparison) and any((isinstance(op.operator, cst.NotEqual) for op in c.comparisons))
            for c in cst.matchers.findall(module, m.Comparison())
        )
    )
    assert has_not_equal
    has_not_isinstance = any(
        (
            isinstance(u, cst.UnaryOperation)
            and isinstance(u.expression, cst.Call)
            and isinstance(u.expression.func, cst.Name)
            and (u.expression.func.value == "isinstance")
            for u in cst.matchers.findall(module, m.UnaryOperation())
        )
    )
    assert has_not_isinstance


def test_assert_raises_regex_match_kw_injection():
    src = "with self.assertRaisesRegex(ValueError, 'bad'):\n    raise ValueError()\n"
    res = _run(src)
    code = res["module"].code
    assert "with pytest.raises(ValueError" in code
    assert "match" in code and "'bad'" in code


def test_comparison_operators_mapped():
    src = "self.assertGreater(a, b)\nself.assertLess(c, d)\nself.assertGreaterEqual(e, f)\nself.assertLessEqual(g, h)\n"
    res = _run(src)
    mod = res["module"]
    comps = list(cst.matchers.findall(mod, m.Comparison()))
    assert len(comps) >= 4


def test_bare_name_assert_raises_and_unknown_left_unchanged():
    src = "with assertRaises(ValueError):\n    raise ValueError()\n"
    res = _run(src)
    assert "with assertRaises" in res["module"].code or "with pytest.raises" in res["module"].code
    src2 = "self.assertSomethingUnknown(x)\n"
    res2 = _run(src2)
    assert "assertSomethingUnknown" in res2["module"].code


def test_collection_equality_structural():
    src = "self.assertListEqual(a, b)\nself.assertDictEqual(c, d)\n"
    res = _run(src)
    comps = list(cst.matchers.findall(res["module"], m.Comparison()))
    assert len(comps) >= 2


def test_assert_false_unary_operation_structure():
    res = _run("self.assertFalse(flag)\n")
    module = res["module"]
    found_not = any(
        (
            isinstance(u, cst.UnaryOperation) and isinstance(u.operator, cst.Not)
            for u in cst.matchers.findall(module, m.UnaryOperation())
        )
    )
    assert found_not


def test_assert_is_none_literal_skipped_and_var_converted():
    res_lit = _run("self.assertIsNone(1)\n")
    assert "self.assertIsNone(1)" in res_lit["module"].code
    res_var = _run("self.assertIsNone(foo)\n")
    assert "assert foo is None" in res_var["module"].code


def test_assert_almost_equal_delta_and_places_and_default():
    res_delta = _run("self.assertAlmostEqual(a, b, delta=0.1)\n")
    assert "abs(a - b)" in res_delta["module"].code
    assert "<= 0.1" in res_delta["module"].code
    res_places = _run("self.assertAlmostEqual(a, b, 2)\n")
    assert "round(a - b, 2)" in res_places["module"].code
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
    assert "with pytest.raises(ValueError" in code
    assert "match" in code and "'bad'" in code


def test_assert_regex_sets_re_import():
    res = _run("self.assertRegex(text, pattern)\n")
    code = res["module"].code
    assert "re.search(" in code
    assert res.get("needs_re_import") is True


def test_basic_boolean_and_membership_and_identity_and_instance():
    res = _run(
        "self.assertTrue(flag)\nself.assertFalse(flag)\nself.assertIn(x, y)\nself.assertNotIn(x, y)\nself.assertIs(a, b)\nself.assertIsNot(a, b)\nself.assertIsInstance(o, T)\nself.assertNotIsInstance(o, T)\n"
    )
    code = res["module"].code
    assert "assert flag" in code
    assert "not flag" in code or "assert not flag" in code
    assert "in y" in code
    assert "not in y" in code
    assert "is b" in code
    assert "is not b" in code
    assert "isinstance(o, T)" in code
    assert "not isinstance(o, T)" in code


def test_aliases_and_collections_and_multi_line_equal():
    res = _run("self.assertEquals(x, y)\n")
    assert "assert x == y" in res["module"].code
    res_col = _run("self.assertListEqual(a, b)\nself.assertDictEqual(a, b)\nself.assertSetEqual(a, b)\n")
    ccode = res_col["module"].code
    assert "a == b" in ccode
    res_multi = _run("self.assertMultiLineEqual(s1, s2)\n")
    assert "s1 == s2" in res_multi["module"].code


def test_assert_almost_equal_non_numeric_third_positional_is_msg():
    res = _run("self.assertAlmostEqual(a, b, 'not-a-number')\n")
    code = res["module"].code
    assert "pytest.approx" in code


def test_assert_is_none_with_simple_string_literal_skipped():
    res = _run("self.assertIsNone('x')\n")
    assert "self.assertIsNone('x')" in res["module"].code


def test_assert_raises_standalone_name_and_non_self_calls():
    res = _run("with assertRaises(ValueError):\n    raise ValueError()\n")
    assert "with assertRaises" in res["module"].code or "with pytest.raises" in res["module"].code


def _mod(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_assert_regex_sets_re_import_and_search_expression():
    src = "\ndef test_it():\n    self.assertRegex(text, pattern)\n"
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    assert "re.search" in new.code
    assert out.get("needs_re_import") is True


def test_assert_not_regex_negates_search_and_sets_re_import():
    src = "\ndef test_it():\n    self.assertNotRegex(text, pattern)\n"
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    assert "not re.search" in new.code or ("re.search(" in new.code and "is None" in new.code)
    assert out.get("needs_re_import") is True


def test_assert_is_none_literal_guard_returns_none_behavior():
    src = "\ndef test_it():\n    self.assertIsNone(1)\n"
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    assert "is None" not in new.code


def test_assert_almost_equal_with_delta_uses_abs_compare():
    src = "\ndef test_it():\n    self.assertAlmostEqual(a, b, delta=0.1)\n"
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    assert "abs" in new.code and "<=" in new.code


def test_assert_not_almost_equal_default_uses_not_approx():
    src = "\ndef test_it():\n    self.assertNotAlmostEqual(a, b)\n"
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    assert "pytest.approx" in new.code


def _out_code(src: str) -> tuple[str, dict]:
    mod = cst.parse_module(src)
    res = assertion_rewriter_stage({"module": mod})
    return (res["module"].code, res)


def test_is_and_is_not_conversions():
    code, _ = _out_code("\ndef test():\n    self.assertIs(a, b)\n    self.assertIsNot(a, b)\n")
    assert "is b" in code
    assert "is not b" in code


def test_in_and_not_in_and_collection_equal():
    code, _ = _out_code(
        "\ndef test():\n    self.assertIn(x, y)\n    self.assertNotIn(x, y)\n    self.assertListEqual(a, b)\n"
    )
    assert "in y" in code
    assert "not in" in code
    assert "== b" in code


def test_isinstance_and_not_isinstance():
    code, _ = _out_code("\ndef test():\n    self.assertIsInstance(x, T)\n    self.assertNotIsInstance(x, T)\n")
    assert "isinstance(x, T)" in code
    assert "not isinstance" in code


def test_comparison_variants():
    code, _ = _out_code(
        "\ndef test():\n    self.assertGreater(a, b)\n    self.assertGreaterEqual(a, b)\n    self.assertLess(a, b)\n    self.assertLessEqual(a, b)\n"
    )
    assert ">" in code
    assert ">=" in code or ">=" in code
    assert "<" in code
    assert "<=" in code or "<=" in code


def test_almost_equal_with_numeric_third_positional_keeps_places():
    code, _ = _out_code("\ndef test():\n    self.assertAlmostEqual(a, b, 3)\n")
    assert "round" in code and ", 3" in code


def test_multi_line_and_regex_variants_present():
    code, res = _out_code(
        "\ndef test():\n    self.assertMultiLineEqual(s1, s2)\n    self.assertRegex(s, pat)\n    self.assertNotRegex(s, pat)\n"
    )
    assert "== s2" in code or "== s2" in code
    assert "re.search" in code
    assert res.get("needs_re_import") is True


def _mod__01(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_assert_false_converts_to_not_expression():
    src = "\ndef test_it():\n    self.assertFalse(x)\n"
    mod = _mod__01(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    assert "assert not x" in new_mod.code


def test_assert_true_on_nested_attr_keeps_attr():
    src = "\ndef test_it():\n    self.assertTrue(foo.bar)\n"
    mod = _mod__01(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    assert "assert foo.bar" in new_mod.code


def test_assert_raises_context_manager_to_pytest_raises():
    src = "\ndef test_it():\n    with self.assertRaises(ValueError):\n        do_thing()\n"
    mod = _mod__01(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    assert "with pytest.raises(ValueError)" in new_mod.code
    assert out.get("needs_pytest_import") is True


def test_assert_almost_equal_uses_approx_and_sets_pytest_flag():
    src = "\ndef test_it():\n    self.assertAlmostEqual(a, b)\n"
    mod = _mod__01(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    assert "pytest.approx" in new_mod.code
    assert out.get("needs_pytest_import") is True


def test_assert_equal_with_msg_keyword_is_stripped():
    src = "\ndef test_it():\n    self.assertEqual(1, 2, msg='boom')\n"
    mod = _mod__01(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    assert "boom" not in new_mod.code


def run(src: str):
    mod = cst.parse_module(src)
    return assertion_rewriter_stage({"module": mod})


@pytest.mark.parametrize(
    "src, expected",
    [
        ("def test():\n    self.assertEqual(a, b)\n", "a == b"),
        ("def test():\n    self.assertNotEqual(x, y)\n", "x != y"),
        ("def test():\n    self.assertTrue(cond)\n", "cond"),
        ("def test():\n    self.assertFalse(cond2)\n", "not cond2"),
        ("def test():\n    self.assertListEqual(l1, l2)\n", "l1 == l2"),
        ("def test():\n    self.assertIs(a, b)\n", "a is b"),
        ("def test():\n    self.assertIsNot(x, y)\n", "x is not y"),
        ("def test():\n    self.assertIn(item, coll)\n", "item in coll"),
        ("def test():\n    self.assertNotIn(item2, coll2)\n", "item2 not in coll2"),
    ],
)
def test_various_simple_assertions(src: str, expected: str):
    out = run(src)
    code = out["module"].code
    assert expected in code


def test_almost_equal_places_and_delta_and_default_approx():
    src1 = "def test():\n    self.assertAlmostEqual(a, b, 3)\n"
    out1 = run(src1)
    code1 = out1["module"].code
    assert "round(" in code1 or "pytest.approx" in code1
    src2 = "def test():\n    self.assertAlmostEqual(a, b, delta=0.1)\n"
    out2 = run(src2)
    code2 = out2["module"].code
    assert "abs(" in code2 and "<= 0.1" in code2
    src3 = "def test():\n    self.assertAlmostEqual(a, b)\n"
    out3 = run(src3)
    code3 = out3["module"].code
    assert "pytest.approx" in code3


def test_regex_and_not_regex_and_re_import():
    src = "def test():\n    self.assertRegex(text, pattern)\n    self.assertNotRegex(text2, pattern2)\n"
    out = run(src)
    code = out["module"].code
    assert "re.search" in code
    assert ("not re.search" in code or "not(" in code) or ("re.search(" in code and "is None" in code)
    assert out.get("needs_re_import", False) is True


def test_raises_call_and_with_are_handled():
    src_call = "def test():\n    self.assertRaises(ValueError, func, arg)\n"
    out_call = run(src_call)
    code_call = out_call["module"].code
    assert "self.assertRaises" in code_call
    src_with = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    out_with = run(src_with)
    code_with = out_with["module"].code
    assert "pytest.raises" in code_with
    assert out_with.get("needs_pytest_import", False) is True


@pytest.mark.parametrize(
    "src, expected_parts, needs_re",
    [
        ("def test():\n    self.assertRegex(text, pattern)\n", ["re.search"], True),
        ("def test():\n    assertRegex(text, pattern)\n", ["re.search"], True),
        ("def test():\n    self.assertRegexpMatches(text, pattern)\n", ["re.search"], True),
        ("def test():\n    self.assertNotRegex(text, pattern)\n", ["re.search", ("not", "is None")], True),
        ("def test():\n    self.assertNotRegexpMatches(text, pattern)\n", ["re.search", ("not", "is None")], True),
    ],
)
def test_regex_variants(src: str, expected_parts: list[str], needs_re: bool):
    out = run(src)
    code = out["module"].code
    for part in expected_parts:
        if isinstance(part, (list, tuple)):
            assert any((p in code for p in part))
        else:
            assert part in code
    assert out.get("needs_re_import", False) is needs_re


@pytest.mark.parametrize(
    "src, expected_checks",
    [
        ("def test():\n    self.assertAlmostEqual(a, b, 3)\n", [lambda s: "round(" in s or "pytest.approx" in s]),
        ("def test():\n    self.assertAlmostEqual(a, b, delta=0.1)\n", [lambda s: "abs(" in s and "<= 0.1" in s]),
        (
            "def test():\n    self.assertAlmostEqual(a, b, places=2)\n",
            [lambda s: "round(" in s or "pytest.approx" in s],
        ),
        ("def test():\n    self.assertAlmostEqual(a, b)\n", [lambda s: "pytest.approx" in s]),
    ],
)
def test_almost_equal_parametrized(src: str, expected_checks: list):
    out = run(src)
    code = out["module"].code
    for check in expected_checks:
        assert check(code)


@pytest.mark.parametrize(
    "src, expected_check",
    [
        ("def test():\n    self.assertNotAlmostEqual(a, b, delta=0.1)\n", lambda s: "abs(" in s and "> 0.1" in s),
        ("def test():\n    self.assertNotAlmostEqual(a, b, 2)\n", lambda s: "round(" in s or "pytest.approx" in s),
        ("def test():\n    self.assertNotAlmostEqual(a, b)\n", lambda s: "pytest.approx" in s),
    ],
)
def test_not_almost_equal_parametrized(src: str, expected_check):
    out = run(src)
    code = out["module"].code
    assert expected_check(code)


@pytest.mark.parametrize(
    "src, expected",
    [
        ("def test():\n    self.assertEqual(a, b, 'maybe')\n", "a == b"),
        ("def test():\n    self.assertEqual(a, b, msg='oops')\n", "a == b"),
        ("def test():\n    self.assertIsNone(x)\n", "x is None"),
        ("def test():\n    self.assertIsNotNone(y)\n", "y is not None"),
    ],
)
def test_msg_and_is_none_variants(src: str, expected: str):
    out = run(src)
    code = out["module"].code
    assert expected in code


@pytest.mark.parametrize(
    "src, expected_contains",
    [
        ("def test():\n    self.assertAlmostEqual(a, b, delta=0.5, places=2)\n", ["abs(", "<= 0.5"]),
        ("def test():\n    self.assertNotAlmostEqual(a, b, places=1)\n", ["round(", ("!= 0", "not round")]),
        ("def test():\n    self.assertAlmostEqual(a, b, 4, places=4)\n", ["round("]),
    ],
)
def test_almost_equal_extra_permutations(src: str, expected_contains: list[str]):
    out = run(src)
    code = out["module"].code
    for part in expected_contains:
        if isinstance(part, (list, tuple)):
            assert any((p in code for p in part))
        else:
            assert part in code


@pytest.mark.parametrize(
    "src, expected",
    [
        ("def test():\n    self.assertRegex(text, pattern, msg='x')\n", "re.search"),
        ("def test():\n    self.assertNotRegex(text, pattern, msg='x')\n", "re.search"),
    ],
)
def test_regex_with_msg_dropped(src: str, expected: str):
    out = run(src)
    code = out["module"].code
    assert expected in code


@pytest.mark.parametrize(
    "src, expected",
    [
        ("def test():\n    self.assertTrue(cond, 'oops')\n", "cond"),
        ("def test():\n    self.assertFalse(cond2, msg='nope')\n", "not cond2"),
        ("def test():\n    self.assertIn(x, y, 'm')\n", "x in y"),
        ("def test():\n    self.assertNotIn(x2, y2, msg='m')\n", "x2 not in y2"),
    ],
)
def test_boolean_and_membership_msg_dropped(src: str, expected: str):
    out = run(src)
    code = out["module"].code
    assert expected in code


@pytest.mark.parametrize(
    "src, expected_parts, needs_re",
    [
        ("def test():\n    self.assertRegex(text, pattern)\n", ["re.search"], True),
        ("def test():\n    self.assertRegexpMatches(text, pattern)\n", ["re.search"], True),
        ("def test():\n    assertRegexpMatches(text, pattern)\n", ["re.search"], True),
        ("def test():\n    self.assertNotRegexpMatches(text, pattern)\n", ["re.search", ("not", "is None")], True),
    ],
)
def test_additional_regex_aliases(src: str, expected_parts: list[str], needs_re: bool):
    out = run(src)
    code = out["module"].code
    for part in expected_parts:
        if isinstance(part, (list, tuple)):
            assert any((p in code for p in part))
        else:
            assert part in code
    assert out.get("needs_re_import", False) is needs_re


@pytest.mark.parametrize(
    "src, expected_contains",
    [
        ("def test():\n    self.assertNotAlmostEqual(a, b, delta=0.2)\n", ["abs(", "> 0.2"]),
        ("def test():\n    self.assertNotAlmostEqual(a, b)\n", [("pytest.approx", "!= 0", "not round")]),
        ("def test():\n    self.assertAlmostEqual(a, b, places=0)\n", [("round(", "pytest.approx")]),
    ],
)
def test_more_almost_not_almost_permutations(src: str, expected_contains: list[str]):
    out = run(src)
    code = out["module"].code
    for part in expected_contains:
        if isinstance(part, (list, tuple)):
            assert any((p in code for p in part))
        else:
            assert part in code


def run_stage(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return (out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False))


def test_assert_equal_to_comparison():
    src = "def test():\n    self.assertEqual(a, b)\n"
    mod, needs_pytest, needs_re = run_stage(src)
    code = mod.code
    assert "a == b" in code
    assert needs_pytest is False
    assert needs_re is False


def test_assert_false_to_not():
    src = "def test():\n    self.assertFalse(x)\n"
    mod, _, _ = run_stage(src)
    assert "not x" in mod.code


def test_assert_almost_equal_with_delta_uses_abs_le():
    src = "def test():\n    self.assertAlmostEqual(a, b, delta=0.1)\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "abs(" in code and "<=" in code
    assert needs_pytest is False


def test_assert_almost_equal_with_places_positional_uses_round():
    src = "def test():\n    self.assertAlmostEqual(a, b, 3)\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "round(" in code and "== 0" in code
    assert needs_pytest is False


def test_assert_not_almost_equal_with_delta_uses_gt():
    src = "def test():\n    self.assertNotAlmostEqual(a, b, delta=0.2)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "abs(" in code and ">" in code


def test_assert_regex_sets_re_import_and_search():
    src = "def test():\n    self.assertRegex(text, pattern)\n"
    mod, _, needs_re = run_stage(src)
    code = mod.code
    assert "re.search" in code
    assert needs_re is True


def test_assert_raises_context_manager_to_pytest_raises__01():
    src = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "pytest.raises(ValueError)" in code
    assert needs_pytest is True


def test_assert_in_and_not_in():
    src = "def test():\n    self.assertIn(x, coll)\n    self.assertNotIn(x, coll)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "in coll" in code
    assert "not in coll" in code


def run_stage__01(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return (out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False))


def test_assert_almost_equal_places_keyword_rounds():
    src = "def test():\n    self.assertAlmostEqual(a, b, places=4)\n"
    mod, _, _ = run_stage__01(src)
    code = mod.code
    assert "round(" in code and "== 0" in code


def test_assert_not_almost_equal_places_keyword_not_rounds():
    src = "def test():\n    self.assertNotAlmostEqual(a, b, places=2)\n"
    mod, _, _ = run_stage__01(src)
    code = mod.code
    assert "round(" in code and ("== 0" in code or "!= 0" in code)


def test_assert_raises_regex_creates_match_kw():
    src = "def test():\n    with self.assertRaisesRegex(ValueError, 'boom'):\n        func()\n"
    mod, needs_pytest, _ = run_stage__01(src)
    code = mod.code
    assert "pytest.raises" in code and "match" in code
    assert needs_pytest is True


def test_msg_keyword_stripped_from_assert_equal():
    src = "def test():\n    self.assertEqual(a, b, msg='x')\n"
    mod, _, _ = run_stage__01(src)
    code = mod.code
    assert "a == b" in code
    assert "x" not in code


def test_bare_assert_equal_name_is_converted():
    src = "def test():\n    assertEqual(a, b)\n"
    mod, _, _ = run_stage__01(src)
    code = mod.code
    assert "a == b" in code


def run_stage__02(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return (out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False))


def test_regex_aliases_and_negative_forms():
    cases = [
        ("assertRegex", False),
        ("assertRegexpMatches", False),
        ("assertNotRegex", True),
        ("assertNotRegexpMatches", True),
    ]
    for method, negative in cases:
        src = f"def test():\n    self.{method}(text, pattern)\n"
        mod, _, needs_re = run_stage__02(src)
        code = mod.code
        assert "re.search" in code
        assert needs_re is True
        if negative:
            assert "is None" in code or ("not" in code and "re.search(" in code)
        else:
            assert "is None" not in code


def test_almost_equal_default_and_variants():
    cases = [
        ("self.assertAlmostEqual(a, b)", True, None),
        ("self.assertAlmostEqual(a, b, 3)", False, "places"),
        ("self.assertAlmostEqual(a, b, places=2)", False, "places"),
        ("self.assertAlmostEqual(a, b, delta=0.1)", False, "delta"),
        ("self.assertNotAlmostEqual(a, b)", True, None),
        ("self.assertNotAlmostEqual(a, b, 1)", False, "places"),
        ("self.assertNotAlmostEqual(a, b, delta=0.2)", False, "delta"),
    ]
    for call_src, needs_pytest_expected, variant in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage__02(src)
        code = mod.code
        if needs_pytest_expected:
            assert needs_pytest is True
            if variant is None and "Not" not in call_src:
                assert "pytest.approx" in code
            if variant is None and "Not" in call_src:
                assert "pytest.approx" in code
        else:
            assert needs_pytest is False
            if variant == "places":
                assert "round(" in code
            if variant == "delta":
                assert "abs(" in code


def test_trailing_and_kwarg_message_variants_removed():
    cases = [
        ("self.assertEqual(a, b, 'm')", "a == b"),
        ("self.assertEqual(a, b, msg='m')", "a == b"),
        ("self.assertNotEqual(a, b, msg=None)", "a != b"),
        ("self.assertEqual(a, b, 123)", "a == b"),
        ("self.assertEqual(a, b, msg=compute())", "a == b"),
    ]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, _, _ = run_stage__02(src)
        code = mod.code
        assert fragment in code
        assert "m" not in code and "123" not in code and ("compute" not in code)


def test_various_edge_case_messages_and_regex_bytes():
    cases = [
        ("self.assertEqual(a, b, msg=f'{a}')", "a == b"),
        ("self.assertEqual(a, b, msg='✓')", "a == b"),
        ("self.assertRegex(text, br'\\d+')", "re.search"),
        ("self.assertIsNone('x')", "self.assertIsNone('x')"),
        ("self.assertIsNotNone(var)", "var is not None"),
    ]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, needs_re = run_stage__02(src)
        code = mod.code
        assert fragment in code


def test_third_positional_non_numeric_is_dropped_as_msg():
    src = "def test():\n    self.assertEqual(a, b, 'maybe a message')\n"
    mod, _, _ = run_stage__02(src)
    code = mod.code
    assert "a == b" in code
    assert "maybe a message" not in code


def test_assert_raises_call_skipped_in_convert_function_form():
    src = "def test():\n    self.assertRaises(ValueError, func, arg)\n"
    mod, _, _ = run_stage__02(src)
    assert "pytest.raises" not in mod.code


def test_insufficient_args_falls_back_to_false_assert():
    src = "def test():\n    self.assertEqual(a)\n"
    mod, _, _ = run_stage__02(src)
    assert "assert False" in mod.code or "False" in mod.code


def test_collection_equality_maps_to_equality():
    src = "def test():\n    self.assertListEqual(lst1, lst2)\n"
    mod, _, _ = run_stage__02(src)
    assert "lst1 == lst2" in mod.code


def test_not_almost_equal_default_uses_approx_and_sets_pytest():
    src = "def test():\n    self.assertNotAlmostEqual(a, b)\n"
    mod, needs_pytest, _ = run_stage__02(src)
    code = mod.code
    assert "pytest.approx" in code
    assert needs_pytest is True


def run_stage__03(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return (out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False))


def test_assert_true_and_false_paths():
    src = "def test():\n    self.assertTrue(cond)\n    self.assertFalse(cond2)\n"
    mod, _, _ = run_stage__03(src)
    code = mod.code
    assert "cond" in code
    assert "not cond2" in code


def test_assert_is_not_none_and_comparisons():
    src = "def test():\n    self.assertIsNotNone(x)\n    self.assertGreater(a, b)\n    self.assertLess(c, d)\n"
    mod, _, _ = run_stage__03(src)
    code = mod.code
    assert "x is not None" in code
    assert "a > b" in code
    assert "c < d" in code


def test_assert_not_equal_maps_to_not_equal():
    src = "def test():\n    self.assertNotEqual(p, q)\n"
    mod, _, _ = run_stage__03(src)
    assert "p != q" in mod.code


def run_stage__04(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return (out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False))


def test_trailing_msg_is_removed_from_assert_equal():
    src = "def test():\n    self.assertEqual(a, b, 'message')\n"
    mod, _, _ = run_stage__04(src)
    code = mod.code
    assert "a == b" in code
    assert "message" not in code


def test_assert_is_none_literal_guard_and_expr():
    src_lit = "def test():\n    self.assertIsNone(1)\n"
    mod_lit, _, _ = run_stage__04(src_lit)
    assert "self.assertIsNone(1)" in mod_lit.code
    src_expr = "def test():\n    self.assertIsNone(x)\n"
    mod_expr, _, _ = run_stage__04(src_expr)
    assert "x is None" in mod_expr.code


def test_assert_is_and_is_not():
    src = "def test():\n    self.assertIs(a, b)\n    self.assertIsNot(a, b)\n"
    mod, _, _ = run_stage__04(src)
    code = mod.code
    assert "a is b" in code
    assert "a is not b" in code


def test_assert_isinstance_and_not_isinstance():
    src = "def test():\n    self.assertIsInstance(obj, Type)\n    self.assertNotIsInstance(obj, Type)\n"
    mod, _, _ = run_stage__04(src)
    code = mod.code
    assert "isinstance" in code
    assert "not isinstance" in code or "not(" in code


def test_assert_almost_equal_default_uses_approx_and_requires_pytest():
    src = "def test():\n    self.assertAlmostEqual(a, b)\n"
    mod, needs_pytest, _ = run_stage__04(src)
    code = mod.code
    assert "pytest.approx" in code
    assert needs_pytest is True


def test_assert_not_regex_sets_re_import_and_not_search():
    src = "def test():\n    self.assertNotRegex(text, pattern)\n"
    mod, _, needs_re = run_stage__04(src)
    code = mod.code
    assert "re.search" in code
    assert needs_re is True
    assert "not" in code and "re.search(" in code or ("re.search(" in code and "is None" in code)


def test_regex_aliases_and_negations_parametrized():
    cases = [
        ("assertRegex", False),
        ("assertRegexpMatches", False),
        ("assertNotRegex", True),
        ("assertNotRegexpMatches", True),
    ]
    for method, negative in cases:
        src = f"def test():\n    self.{method}(text, pattern)\n"
        mod, _, needs_re = run_stage__04(src)
        code = mod.code
        assert "re.search" in code
        assert needs_re is True
        if negative:
            assert "is None" in code or ("not" in code and "re.search(" in code)
        else:
            assert "is None" not in code


def test_almost_equal_permutations_parametrized():
    cases = [
        ("self.assertAlmostEqual(a, b)", True, None),
        ("self.assertAlmostEqual(a, b, 2)", False, "places"),
        ("self.assertAlmostEqual(a, b, places=3)", False, "places"),
        ("self.assertAlmostEqual(a, b, delta=0.1)", False, "delta"),
        ("self.assertNotAlmostEqual(a, b)", True, None),
        ("self.assertNotAlmostEqual(a, b, 1)", False, "places"),
        ("self.assertNotAlmostEqual(a, b, delta=0.2)", False, "delta"),
    ]
    for call_src, needs_pytest_expected, variant in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage__04(src)
        code = mod.code
        if needs_pytest_expected:
            assert needs_pytest is True
            if variant is None and "Not" not in call_src:
                assert "pytest.approx" in code
            if variant is None and "Not" in call_src:
                assert "pytest.approx" in code and ("!=" in code or "NotEqual" in code)
        else:
            assert needs_pytest is False
            if variant == "places":
                assert "round(" in code
            if variant == "delta":
                assert "abs(" in code and ("<=" in code or ">" in code)


def test_equal_and_not_equal_with_trailing_msg_parametrized():
    cases = [
        ("self.assertEqual(a, b, 'msg')", "a == b", False),
        ("self.assertNotEqual(a, b, 'msg')", "a != b", False),
        ("self.assertEqual(a, b, msg='m')", "a == b", False),
    ]
    for call_src, expected_fragment, needs_pytest in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest_flag, _ = run_stage__04(src)
        code = mod.code
        assert expected_fragment in code
        assert "msg" not in code and "m" not in code


def test_true_false_and_unary_negation_parametrized():
    cases = [("self.assertTrue(a)", "assert a"), ("self.assertFalse(a)", "assert ")]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, _, _ = run_stage__04(src)
        code = mod.code
        assert "assert" in code
        if "assertFalse" in call_src:
            assert "not" in code or "assert " in code


def test_membership_asserts_parametrized():
    cases = [("self.assertIn(x, y)", "in"), ("self.assertNotIn(x, y)", "not in")]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, _, _ = run_stage__04(src)
        code = mod.code
        assert fragment in code


def test_assert_raises_and_regex_context_manager_conversions():
    src = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    mod, needs_pytest, _ = run_stage__04(src)
    code = mod.code
    assert "pytest.raises" in code
    assert needs_pytest is True
    src2 = "def test():\n    with self.assertRaisesRegex(ValueError, 'msg'):\n        func()\n"
    mod2, needs_pytest2, _ = run_stage__04(src2)
    code2 = mod2.code
    assert "pytest.raises" in code2 and "match" in code2
    assert needs_pytest2 is True


def test_assert_is_not_none_and_literal_guards():
    src_expr = "def test():\n    self.assertIsNotNone(x)\n"
    mod_expr, _, _ = run_stage__04(src_expr)
    assert "x is not None" in mod_expr.code


def test_not_isinstance_emits_unary_not():
    src = "def test():\n    self.assertNotIsInstance(obj, Type)\n"
    mod, _, _ = run_stage__04(src)
    code = mod.code
    assert "isinstance" in code and ("not" in code or "not isinstance" in code)


def test_more_parametrized_variants_batch2():
    cases = [
        ("self.assertRegex(text, r'\\d+')", "re.search", False),
        ("self.assertEqual(a, b, f'msg{a}')", "a == b", False),
        ("self.assertIsNone(42)", "self.assertIsNone(42)", False),
        ("self.assertIsNone(var)", "var is None", False),
        ("self.assertIsNotNone(var)", "var is not None", False),
        ("self.assertIs(a, b)", "a is b", False),
        ("self.assertIsNot(a, b)", "a is not b", False),
        ("self.assertNotIn(x, func())", "not in", False),
        ("self.assertTrue(a == b)", "a == b", False),
        ("self.assertFalse(check())", "not", False),
        ("self.assertEqual(a, b, msg=str(1))", "a == b", False),
    ]
    for call_src, fragment, _ in cases:
        src = f"def test():\n    {call_src}\n"
        mod, _, _ = run_stage__04(src)
        code = mod.code
        assert fragment in code


def test_message_permutations_and_edge_cases():
    cases = [
        ("self.assertEqual(a, b, msg=None)", "a == b", False),
        ("self.assertEqual(a, b, msg=message)", "a == b", False),
        ("self.assertAlmostEqual(a, b, 'oops')", "pytest.approx", True),
        ("self.assertAlmostEqual(a, b, places=2, delta=0.05)", "abs(", False),
        ("self.assertNotAlmostEqual(a, b, delta=0.3)", "abs(", False),
        ("with self.assertRaises(ValueError) as cm:\n        f()", "with pytest.raises", True),
        ("self.assertRegex(text, r'(foo)\\1')", "re.search", False),
        ("self.assertIsNone('x')", "self.assertIsNone('x')", False),
        ("self.assertTrue(check())", "check()", False),
        ("self.assertFalse(a == b)", "not", False),
        ("self.assertEqual(a, b, 'tr')", "a == b", False),
    ]
    for call_src, fragment, expect_pytest in cases:
        if call_src.startswith("with "):
            src = f"def test():\n    {call_src}\n"
        else:
            src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage__04(src)
        code = mod.code
        assert fragment in code
        if expect_pytest:
            assert needs_pytest is True
        else:
            pass


def test_more_messages_and_kwarg_edge_cases():
    cases = [
        ("self.assertEqual(a, b, '')", "a == b"),
        ("self.assertEqual(a, b, 123)", "a == b"),
        ("self.assertEqual(a, b, msg=compute())", "a == b"),
        ("self.assertAlmostEqual(a, b, 2.0)", "round("),
        ("self.assertAlmostEqual(a, b, unexpected='x')", "pytest.approx"),
        ("self.assertNotEqual(a, b, ('x','y'))", "a != b"),
        ("self.assertIn(x, y, msg='m')", "in"),
        ("self.assertIsNone((x))", "is None"),
        ("self.assertIsNotNone(0)", "0 is not None" if False else "0 is not None"),
        ("self.assertTrue(a < b < c)", "< b <"),
        ("self.assertFalse(obj.is_ok())", "obj.is_ok()"),
    ]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage__04(src)
        code = mod.code
        assert fragment in code


def test_more_messages_batch4_edge_cases():
    cases = [
        ("self.assertEqual(a, b, msg='✓ success')", "a == b"),
        ("self.assertEqual(a, b, msg=f'val={a}')", "a == b"),
        ("self.assertNotEqual(a, b, msg=None)", "a != b"),
        ("self.assertEqual(a, b, msg=True)", "a == b"),
        ("self.assertEqual(a, b, 'line1\\nline2')", "a == b"),
        ("self.assertEqual(a, b, msg={'k':1})", "a == b"),
        ("self.assertAlmostEqual(a, b, places=0)", "round("),
        ("self.assertAlmostEqual(a, b, delta=0)", "abs("),
        ("self.assertNotAlmostEqual(a, b, places=0)", "round("),
        ("self.assertCountEqual(a, b, msg='x')", "=="),
        ("self.assertRegex(text, pattern)", "re.search"),
    ]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage__04(src)
        code = mod.code
        assert fragment in code


def test_more_parametrized_batch3_collections_and_comparisons():
    cases = [
        ("self.assertEquals(a, b)", "a == b"),
        ("self.assertAlmostEquals(a, b)", "pytest.approx"),
        ("self.assertItemsEqual(a, b)", "=="),
        ("self.assertCountEqual(a, b)", "=="),
        ("self.assertListEqual(a, b)", "=="),
        ("self.assertSequenceEqual(a, b)", "=="),
        ("self.assertSetEqual(a, b)", "=="),
        ("self.assertGreater(a, b)", ">"),
        ("self.assertGreaterEqual(a, b)", ">="),
        ("self.assertLess(a, b)", "<"),
        ("self.assertLessEqual(a, b)", "<="),
        ("self.assertMultiLineEqual(a, b)", "=="),
    ]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage__04(src)
        code = mod.code
        assert fragment in code
        if "pytest.approx" in fragment or "AlmostEquals" in call_src:
            assert needs_pytest is True


def test_assert_raises_regexp_alias_and_msg_removal():
    src = "def test():\n    with self.assertRaisesRegexp(ValueError, 'err'):\n        f()\n"
    mod, needs_pytest, _ = run_stage__04(src)
    code = mod.code
    assert "pytest.raises" in code and "match" in code and (needs_pytest is True) or "assertRaisesRegexp" in code
    src2 = "def test():\n    self.assertNotEqual(a, b, msg='m')\n"
    mod2, _, _ = run_stage__04(src2)
    code2 = mod2.code
    assert "a != b" in code2
    assert "m" not in code2
