import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def run_stage(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False)


def test_regex_aliases_and_negative_forms():
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
            # accept canonical 'is None' or unary-not form
            assert "is None" in code or ("not" in code and "re.search(" in code)
        else:
            assert "is None" not in code


def test_almost_equal_default_and_variants():
    cases = [
        ("self.assertAlmostEqual(a, b)", True, None),
        ("self.assertAlmostEqual(a, b, 3)", False, 'places'),
        ("self.assertAlmostEqual(a, b, places=2)", False, 'places'),
        ("self.assertAlmostEqual(a, b, delta=0.1)", False, 'delta'),
        ("self.assertNotAlmostEqual(a, b)", True, None),
        ("self.assertNotAlmostEqual(a, b, 1)", False, 'places'),
        ("self.assertNotAlmostEqual(a, b, delta=0.2)", False, 'delta'),
    ]
    for call_src, needs_pytest_expected, variant in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, _ = run_stage(src)
        code = mod.code
        if needs_pytest_expected:
            assert needs_pytest is True
            if variant is None and 'Not' not in call_src:
                assert "pytest.approx" in code
            if variant is None and 'Not' in call_src:
                assert "pytest.approx" in code
        else:
            assert needs_pytest is False
            if variant == 'places':
                assert "round(" in code
            if variant == 'delta':
                assert "abs(" in code


def test_trailing_and_kwarg_message_variants_removed():
    cases = [
        ("self.assertEqual(a, b, 'm')", 'a == b'),
        ("self.assertEqual(a, b, msg='m')", 'a == b'),
        ("self.assertNotEqual(a, b, msg=None)", 'a != b'),
        ("self.assertEqual(a, b, 123)", 'a == b'),
        ("self.assertEqual(a, b, msg=compute())", 'a == b'),
    ]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, _, _ = run_stage(src)
        code = mod.code
        assert fragment in code
        # message tokens should not survive
        assert 'm' not in code and '123' not in code and 'compute' not in code


def test_various_edge_case_messages_and_regex_bytes():
    cases = [
        ("self.assertEqual(a, b, msg=f'{a}')", 'a == b'),
        ("self.assertEqual(a, b, msg='✓')", 'a == b'),
        ("self.assertRegex(text, br'\\d+')", 're.search'),
        ("self.assertIsNone('x')", "self.assertIsNone('x')"),
        ("self.assertIsNotNone(var)", 'var is not None'),
    ]
    for call_src, fragment in cases:
        src = f"def test():\n    {call_src}\n"
        mod, needs_pytest, needs_re = run_stage(src)
        code = mod.code
        assert fragment in code

def test_third_positional_non_numeric_is_dropped_as_msg():
    src = "def test():\n    self.assertEqual(a, b, 'maybe a message')\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "a == b" in code
    assert "maybe a message" not in code


def test_assert_raises_call_skipped_in_convert_function_form():
    # ensure that assertRaises as a Call (not With) is skipped by conversion
    src = "def test():\n    self.assertRaises(ValueError, func, arg)\n"
    mod, _, _ = run_stage(src)
    # skipped means original call stays (no pytest.raises created)
    assert "pytest.raises" not in mod.code


def test_insufficient_args_falls_back_to_false_assert():
    src = "def test():\n    self.assertEqual(a)\n"
    mod, _, _ = run_stage(src)
    # fallback to assert False when args are missing
    assert "assert False" in mod.code or "False" in mod.code


def test_collection_equality_maps_to_equality():
    src = "def test():\n    self.assertListEqual(lst1, lst2)\n"
    mod, _, _ = run_stage(src)
    assert "lst1 == lst2" in mod.code


def test_not_almost_equal_default_uses_approx_and_sets_pytest():
    src = "def test():\n    self.assertNotAlmostEqual(a, b)\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "pytest.approx" in code
    assert needs_pytest is True
