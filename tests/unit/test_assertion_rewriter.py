import libcst as cst
import libcst.matchers as m

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


def test_assert_almost_equal_sets_approx_flag():
    s = """
class Test:
    def test_approx(self):
        a = 1.0
        b = 1.000001
        self.assertAlmostEqual(a, b)
"""

    res = _run(s)
    # approx conversion should require pytest import
    assert res.get("needs_pytest_import", False) is True


def test_assert_regex_sets_re_import_and_uses_search():
    s = """
class Test:
    def test_re(self):
        self.assertRegex('abc', r'b')
        self.assertNotRegex('abc', r'z')
"""

    res = _run(s)
    # regex assertions should request re import
    assert res.get("needs_re_import", False) is True
    # structural check: ensure a call to re.search exists somewhere
    module = res["module"]
    # collect Assert nodes using a visitor to avoid structural assumptions
    found_asserts: list[cst.Assert] = []

    class AVisitor(cst.CSTVisitor):
        def visit_Assert(self, node: cst.Assert) -> None:  # type: ignore[override]
            found_asserts.append(node)

    module.visit(AVisitor())

    # find an Assert whose test is a Call to re.search
    found_search = any(
        isinstance(a.test, cst.Call)
        and isinstance(a.test.func, cst.Attribute)
        and isinstance(a.test.func.value, cst.Name)
        and a.test.func.value.value == "re"
        and isinstance(a.test.func.attr, cst.Name)
        and a.test.func.attr.value == "search"
        for a in found_asserts
    )
    assert found_search, "expected re.search call in converted code"


def test_assert_raises_context_and_callable_form():
    s = """
class Test:
    def test_raises_ctx(self):
        with self.assertRaises(ValueError):
            int('x')

    def test_raises_callable(self):
        self.assertRaises(ValueError, int, 'x')
"""

    res = _run(s)
    module = res["module"]
    # Robust check: find any Call node that is pytest.raises(...)
    found_with_raises = any(
        isinstance(call.func, cst.Attribute)
        and isinstance(call.func.value, cst.Name)
        and call.func.value.value == 'pytest'
        and isinstance(call.func.attr, cst.Name)
        and call.func.attr.value == 'raises'
        for call in cst.matchers.findall(module, m.Call())
    )

    assert found_with_raises is True
    assert res.get("needs_pytest_import", False) is True

    # Ensure the callable form (self.assertRaises(...)) remains as a Call to attribute 'assertRaises'
    found_callable = any(
        isinstance(call.func, cst.Attribute)
        and isinstance(call.func.attr, cst.Name)
        and call.func.attr.value == 'assertRaises'
        for call in cst.matchers.findall(module, m.Call())
    )
    assert found_callable is True


def test_identity_and_membership_operators():
    s = """
class Test:
    def test_ops(self):
        a = object()
        b = a
        items = [1,2]
        self.assertIs(a, b)
        self.assertIsNot(a, None)
        self.assertIn(2, items)
        self.assertNotIn(3, items)
"""

    res = _run(s)
    module = res["module"]
    # look for Comparison nodes with Is/IsNot and In/NotIn
    found_is = found_isnot = found_in = found_notin = False
    for node in cst.matchers.findall(module, m.Comparison()):
        # comparisons have .comparisons list with operators
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
    s = """
class Test:
    def test_truth(self):
        x = None
        self.assertTrue(x is None)
        self.assertFalse(x)
"""

    res = _run(s)
    module = res["module"]
    # collect Assert nodes
    found_asserts: list[cst.Assert] = []

    class AVisitor2(cst.CSTVisitor):
        def visit_Assert(self, node: cst.Assert) -> None:  # type: ignore[override]
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
    # places kw -> round(..., places) == 0
    res_places_kw = _run("self.assertAlmostEqual(a, b, places=3)\n")
    assert "round(a - b, 3)" in res_places_kw["module"].code

    # assertNotAlmostEqual with numeric third positional should produce a Not(round(...) == 0)
    res_not_places = _run("self.assertNotAlmostEqual(a, b, 2)\n")
    # structure: UnaryOperation(Not, Comparison(left=round(...), comparisons=[Equal(0)]))
    has_not_round = any(
        isinstance(node, cst.UnaryOperation)
        and isinstance(node.expression, cst.Comparison)
        for node in cst.matchers.findall(res_not_places["module"], m.UnaryOperation())
    )
    assert has_not_round


def test_assert_not_regex_structural_not_search():
    res = _run("self.assertNotRegex(text, pattern)\n")
    module = res["module"]
    # expect a UnaryOperation(Not, Call(re.search(...))) somewhere
    found_not_search = False
    for un in cst.matchers.findall(module, m.UnaryOperation()):
        # check inner expression is a Call whose func is re.search
        inner = getattr(un, "expression", None)
        if isinstance(inner, cst.Call) and isinstance(inner.func, cst.Attribute) and isinstance(inner.func.value, cst.Name) and inner.func.value.value == 're' and isinstance(inner.func.attr, cst.Name) and inner.func.attr.value == 'search':
            found_not_search = True
            break
    assert found_not_search is True


def test_assert_is_not_none_and_not_equal_and_not_is_instance():
    s = """
class Test:
    def test_ops(self):
        a = None
        b = 1
        self.assertIsNotNone(a)
        self.assertNotEqual(a, b)
        self.assertNotIsInstance(a, int)
"""

    res = _run(s)
    module = res["module"]
    # assertIsNotNone -> Comparison with IsNot None
    has_is_not_none = any(
        isinstance(c, cst.Comparison) and any(isinstance(op.operator, cst.IsNot) for op in c.comparisons)
        for c in cst.matchers.findall(module, m.Comparison())
    )
    assert has_is_not_none

    # assertNotEqual -> Comparison with NotEqual operator
    has_not_equal = any(
        isinstance(c, cst.Comparison) and any(isinstance(op.operator, cst.NotEqual) for op in c.comparisons)
        for c in cst.matchers.findall(module, m.Comparison())
    )
    assert has_not_equal

    # assertNotIsInstance -> UnaryOperation(Not, Call(func=Name('isinstance')))
    has_not_isinstance = any(
        isinstance(u, cst.UnaryOperation) and isinstance(u.expression, cst.Call) and isinstance(u.expression.func, cst.Name) and u.expression.func.value == 'isinstance'
        for u in cst.matchers.findall(module, m.UnaryOperation())
    )
    assert has_not_isinstance


def test_assert_raises_regex_match_kw_injection():
    # assertRaisesRegex should convert to pytest.raises(..., match=...)
    src = "with self.assertRaisesRegex(ValueError, 'bad'):\n    raise ValueError()\n"
    res = _run(src)
    code = res["module"].code
    assert "with pytest.raises(ValueError" in code
    assert "match" in code and "'bad'" in code


def test_comparison_operators_mapped():
    # Ensure greater/less comparisons are emitted for corresponding asserts
    src = "self.assertGreater(a, b)\nself.assertLess(c, d)\nself.assertGreaterEqual(e, f)\nself.assertLessEqual(g, h)\n"
    res = _run(src)
    mod = res["module"]
    # check presence of comparison operators by looking at Comparison nodes
    comps = list(cst.matchers.findall(mod, m.Comparison()))
    assert len(comps) >= 4


def test_bare_name_assert_raises_and_unknown_left_unchanged():
    # with assertRaises (bare name) should be allowed; stage handles self.assertRaises specifically but we
    # ensure the pipeline returns a module and sets no exception
    src = "with assertRaises(ValueError):\n    raise ValueError()\n"
    res = _run(src)
    assert "with assertRaises" in res["module"].code or "with pytest.raises" in res["module"].code

    # unknown assertion method (not in map) should remain as a Call expression unchanged
    src2 = "self.assertSomethingUnknown(x)\n"
    res2 = _run(src2)
    # the original call should remain (conservative behavior)
    assert "assertSomethingUnknown" in res2["module"].code


def test_collection_equality_structural():
    # collection equality variants map to equality comparison
    src = "self.assertListEqual(a, b)\nself.assertDictEqual(c, d)\n"
    res = _run(src)
    comps = list(cst.matchers.findall(res["module"], m.Comparison()))
    # expect at least two comparisons emitted
    assert len(comps) >= 2


def test_assert_false_unary_operation_structure():
    res = _run("self.assertFalse(flag)\n")
    module = res["module"]
    # assertFalse maps to UnaryOperation(Not, expression=flag)
    found_not = any(
        isinstance(u, cst.UnaryOperation) and isinstance(u.operator, cst.Not)
        for u in cst.matchers.findall(module, m.UnaryOperation())
    )
    assert found_not


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
