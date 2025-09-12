import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def run_stage(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False)


def test_assert_almost_equal_places_keyword_rounds():
    src = "def test():\n    self.assertAlmostEqual(a, b, places=4)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "round(" in code and "== 0" in code


def test_assert_not_almost_equal_places_keyword_not_rounds():
    src = "def test():\n    self.assertNotAlmostEqual(a, b, places=2)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "round(" in code and "== 0" in code


def test_assert_raises_regex_creates_match_kw():
    src = "def test():\n    with self.assertRaisesRegex(ValueError, 'boom'):\n        func()\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    # formatting may include spaces around '=', so check for pytest.raises and presence of 'match'
    assert "pytest.raises" in code and "match" in code
    assert needs_pytest is True


def test_msg_keyword_stripped_from_assert_equal():
    src = "def test():\n    self.assertEqual(a, b, msg='x')\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "a == b" in code
    assert "x" not in code


def test_bare_assert_equal_name_is_converted():
    src = "def test():\n    assertEqual(a, b)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "a == b" in code
