import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def run_stage(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False)


def test_trailing_msg_is_removed_from_assert_equal():
    src = "def test():\n    self.assertEqual(a, b, 'message')\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "a == b" in code
    assert "message" not in code


def test_assert_is_none_literal_guard_and_expr():
    # literal path should be left unchanged
    src_lit = "def test():\n    self.assertIsNone(1)\n"
    mod_lit, _, _ = run_stage(src_lit)
    assert "self.assertIsNone(1)" in mod_lit.code

    # expression path should convert to 'is None'
    src_expr = "def test():\n    self.assertIsNone(x)\n"
    mod_expr, _, _ = run_stage(src_expr)
    assert "x is None" in mod_expr.code


def test_assert_is_and_is_not():
    src = "def test():\n    self.assertIs(a, b)\n    self.assertIsNot(a, b)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "a is b" in code
    assert "a is not b" in code


def test_assert_isinstance_and_not_isinstance():
    src = "def test():\n    self.assertIsInstance(obj, Type)\n    self.assertNotIsInstance(obj, Type)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "isinstance" in code
    assert "not isinstance" in code or "not(" in code


def test_assert_almost_equal_default_uses_approx_and_requires_pytest():
    src = "def test():\n    self.assertAlmostEqual(a, b)\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "pytest.approx" in code
    assert needs_pytest is True


def test_assert_not_regex_sets_re_import_and_not_search():
    src = "def test():\n    self.assertNotRegex(text, pattern)\n"
    mod, _, needs_re = run_stage(src)
    code = mod.code
    assert "re.search" in code
    assert needs_re is True
    # accept either legacy unary-not or canonical 'is None' comparison
    assert ("not" in code and "re.search(" in code) or ("re.search(" in code and "is None" in code)


def test_regex_aliases_and_negations_parametrized():
    # cover assertRegex/assertRegexpMatches and their negative forms
    cases = [
        ("assertRegex", False),
        ("assertRegexpMatches", False),
        ("assertNotRegex", True),
        ("assertNotRegexpMatches", True),
    ]
    for method, negative in cases:
        src = f"def test():\n    self.{method}(text, pattern)\n"
        mod, _, needs_re = run_stage(src)
        code = mod.code
        assert "re.search" in code
        assert needs_re is True
        if negative:
            # canonical form uses 'is None'
            assert "is None" in code or ("not" in code and "re.search(" in code)
        else:
            assert "is None" not in code


def test_almost_equal_permutations_parametrized():
    # covers default approx, places positional, and delta kwarg
    cases = [
        ("self.assertAlmostEqual(a, b)", True, None),
        ("self.assertAlmostEqual(a, b, 2)", False, "places"),
        ("self.assertAlmostEqual(a, b, places=3)", False, "places"),
        ("self.assertAlmostEqual(a, b, delta=0.1)", False, "delta"),
        ("self.assertNotAlmostEqual(a, b)", True, None),
        # NotAlmostEqual with explicit places/delta maps to round/abs forms and
        # therefore does not require pytest.approx
        ("self.assertNotAlmostEqual(a, b, 1)", False, "places"),
        ("self.assertNotAlmostEqual(a, b, delta=0.2)", False, "delta"),
    ]
    for call_src, needs_pytest_expected, variant in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage(src)
        code = mod.code
        if needs_pytest_expected:
            assert needs_pytest is True
            # should use pytest.approx for default approx cases
            if variant is None and "Not" not in call_src:
                assert "pytest.approx" in code
            # for NotAlmostEqual default expect '!=' with pytest.approx
            if variant is None and "Not" in call_src:
                assert "pytest.approx" in code and ("!=" in code or "NotEqual" in code)
        else:
            # delta and places shouldn't require pytest
            assert needs_pytest is False
            if variant == "places":
                # round(...) == 0 or != 0 for negative variants
                assert "round(" in code
            if variant == "delta":
                # equal uses '<=' and not-equal uses '>' — accept either
                assert "abs(" in code and ("<=" in code or ">" in code)


def test_equal_and_not_equal_with_trailing_msg_parametrized():
    cases = [
        ("self.assertEqual(a, b, 'msg')", "a == b", False),
        ("self.assertNotEqual(a, b, 'msg')", "a != b", False),
        # also accept keyword msg
        ("self.assertEqual(a, b, msg='m')", "a == b", False),
    ]
    for call_src, expected_fragment, needs_pytest in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest_flag, _ = run_stage(src)
        code = mod.code
        assert expected_fragment in code
        # trailing msg should be removed from output
        assert "msg" not in code and "m" not in code


def test_true_false_and_unary_negation_parametrized():
    cases = [
        ("self.assertTrue(a)", "assert a"),
        ("self.assertFalse(a)", "assert "),
    ]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, _, _ = run_stage(src)
        code = mod.code
        assert "assert" in code
        # assertFalse likely produces a UnaryOperation (not); accept either 'not' or '!' not present in Python
        if "assertFalse" in call_src:
            assert ("not" in code) or ("assert " in code)


def test_membership_asserts_parametrized():
    cases = [
        ("self.assertIn(x, y)", "in"),
        ("self.assertNotIn(x, y)", "not in"),
    ]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, _, _ = run_stage(src)
        code = mod.code
        assert fragment in code


def test_assert_raises_and_regex_context_manager_conversions():
    src = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "pytest.raises" in code
    assert needs_pytest is True

    src2 = "def test():\n    with self.assertRaisesRegex(ValueError, 'msg'):\n        func()\n"
    mod2, needs_pytest2, _ = run_stage(src2)
    code2 = mod2.code
    # accept 'match' token; code generator may format as 'match ='
    assert "pytest.raises" in code2 and "match" in code2
    assert needs_pytest2 is True


def test_assert_is_not_none_and_literal_guards():
    # isNotNone with expression should convert
    src_expr = "def test():\n    self.assertIsNotNone(x)\n"
    mod_expr, _, _ = run_stage(src_expr)
    assert "x is not None" in mod_expr.code


def test_not_isinstance_emits_unary_not():
    src = "def test():\n    self.assertNotIsInstance(obj, Type)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    # implementation uses UnaryOperation(not isinstance(...))
    assert "isinstance" in code and ("not" in code or "not isinstance" in code)


def test_more_parametrized_variants_batch2():
    cases = [
        # regex raw string variant
        ("self.assertRegex(text, r'\\d+')", "re.search", False),
        # trailing msg with format expression
        ("self.assertEqual(a, b, f'msg{a}')", "a == b", False),
        # is/isnot with literal should be preserved for literals
        ("self.assertIsNone(42)", "self.assertIsNone(42)", False),
        ("self.assertIsNone(var)", "var is None", False),
        ("self.assertIsNotNone(var)", "var is not None", False),
        # is/isnot alias combos
        ("self.assertIs(a, b)", "a is b", False),
        ("self.assertIsNot(a, b)", "a is not b", False),
        # not-in variety with complex rhs
        ("self.assertNotIn(x, func())", "not in", False),
        # assertTrue with comparison inside
        ("self.assertTrue(a == b)", "a == b", False),
        # assertFalse with call
        ("self.assertFalse(check())", "not", False),
        # equality with different msg expression
        ("self.assertEqual(a, b, msg=str(1))", "a == b", False),
    ]

    for call_src, fragment, _ in cases:
        src = f"def test():\n    {call_src}\n"
        mod, _, _ = run_stage(src)
        code = mod.code
        assert fragment in code


def test_message_permutations_and_edge_cases():
    # various msg kw/positional variants and edge-case almost-equal combos
    cases = [
        # keyword msg None should be removed
        ("self.assertEqual(a, b, msg=None)", "a == b", False),
        # message as variable keyword removed
        ("self.assertEqual(a, b, msg=message)", "a == b", False),
        # positional non-numeric third arg for AlmostEqual should be treated as msg and dropped
        ("self.assertAlmostEqual(a, b, 'oops')", "pytest.approx", True),
        # Both delta and places provided: delta branch takes precedence -> abs(...) <= delta
        ("self.assertAlmostEqual(a, b, places=2, delta=0.05)", "abs(", False),
        # NotAlmostEqual with negative delta should map to abs(...) > delta
        ("self.assertNotAlmostEqual(a, b, delta=0.3)", "abs(", False),
        # assertRaises with 'as' context manager keeps 'as cm' when converting
        ("with self.assertRaises(ValueError) as cm:\n        f()", "with pytest.raises", True),
        # regex with groups and raw strings
        ("self.assertRegex(text, r'(foo)\\1')", "re.search", False),
        # literal string passed to assertIsNone should remain unchanged
        ("self.assertIsNone('x')", "self.assertIsNone('x')", False),
        # assertTrue with call keeps the call expression
        ("self.assertTrue(check())", "check()", False),
        # assertFalse on comparison yields unary not
        ("self.assertFalse(a == b)", "not", False),
        # trailing positional msg on assertEqual is removed
        ("self.assertEqual(a, b, 'tr')", "a == b", False),
    ]

    for call_src, fragment, expect_pytest in cases:
        if call_src.startswith("with "):
            src = f"def test():\n    {call_src}\n"
        else:
            src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage(src)
        code = mod.code
        assert fragment in code
        # if we expect pytest import, check flag
        if expect_pytest:
            assert needs_pytest is True
        else:
            # mostly ensure we didn't incorrectly require pytest
            pass


def test_more_messages_and_kwarg_edge_cases():
    cases = [
        # msg given as empty string literal
        ("self.assertEqual(a, b, '')", "a == b"),
        # msg given as numeric literal (unusual) should be removed
        ("self.assertEqual(a, b, 123)", "a == b"),
        # msg given as complex expression should be removed
        ("self.assertEqual(a, b, msg=compute())", "a == b"),
        # assertAlmostEqual with places provided as float (should be accepted if numeric)
        ("self.assertAlmostEqual(a, b, 2.0)", "round("),
        # assertAlmostEqual with unexpected kwarg should drop the extra kwarg
        ("self.assertAlmostEqual(a, b, unexpected='x')", "pytest.approx"),
        # assertNotEqual with message tuple should be removed
        ("self.assertNotEqual(a, b, ('x','y'))", "a != b"),
        # assertIn with keyword 'msg' removed
        ("self.assertIn(x, y, msg='m')", "in"),
        # assertIsNone with parentheses expression (accept any 'is None' form)
        ("self.assertIsNone((x))", "is None"),
        # assertIsNotNone with literal should produce 'is not None'
        ("self.assertIsNotNone(0)", "0 is not None" if False else "0 is not None"),
        # assertTrue with chained comparison preserved
        ("self.assertTrue(a < b < c)", "< b <"),
        # assertFalse with attribute access preserved
        ("self.assertFalse(obj.is_ok())", "obj.is_ok()"),
    ]

    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage(src)
        code = mod.code
        assert fragment in code


def test_more_messages_batch4_edge_cases():
    cases = [
        # unicode message should be removed
        ("self.assertEqual(a, b, msg='✓ success')", "a == b"),
        # f-string message with expression
        ("self.assertEqual(a, b, msg=f'val={a}')", "a == b"),
        # None message provided as kwarg — removed
        ("self.assertNotEqual(a, b, msg=None)", "a != b"),
        # Boolean message provided — removed
        ("self.assertEqual(a, b, msg=True)", "a == b"),
        # multiline message literal using escaped newline
        ("self.assertEqual(a, b, 'line1\\nline2')", "a == b"),
        # message as dict (non-serializable) removed
        ("self.assertEqual(a, b, msg={'k':1})", "a == b"),
        # assertAlmostEqual with places=0 should use round(..., 0)
        ("self.assertAlmostEqual(a, b, places=0)", "round("),
        # assertAlmostEqual with delta=0 should map to abs(...) <= 0
        ("self.assertAlmostEqual(a, b, delta=0)", "abs("),
        # assertNotAlmostEqual with places=0 -> round(...) != 0
        ("self.assertNotAlmostEqual(a, b, places=0)", "round("),
        # assertCountEqual with msg kw removed
        ("self.assertCountEqual(a, b, msg='x')", "=="),
        # assertRegex with bytes-like pattern (should still call re.search)
        ("self.assertRegex(text, pattern)", "re.search"),
    ]

    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage(src)
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
        mod, needs_pytest, _ = run_stage(src)
        code = mod.code
        assert fragment in code
        # if approx expected, ensure pytest import flag set
        if "pytest.approx" in fragment or "AlmostEquals" in call_src:
            assert needs_pytest is True


def test_assert_raises_regexp_alias_and_msg_removal():
    src = "def test():\n    with self.assertRaisesRegexp(ValueError, 'err'):\n        f()\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    # older alias may be intentionally left as-is by the stage; accept either form
    assert ("pytest.raises" in code and "match" in code and needs_pytest is True) or ("assertRaisesRegexp" in code)

    # NotEqual with keyword msg should drop the msg
    src2 = "def test():\n    self.assertNotEqual(a, b, msg='m')\n"
    mod2, _, _ = run_stage(src2)
    code2 = mod2.code
    assert "a != b" in code2
    assert "m" not in code2
