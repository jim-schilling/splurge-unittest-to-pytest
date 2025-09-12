import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def run_stage(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False)


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
