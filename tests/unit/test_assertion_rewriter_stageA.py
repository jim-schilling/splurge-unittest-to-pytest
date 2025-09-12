import libcst as cst

from splurge_unittest_to_pytest.stages import assertion_rewriter


def _run_rewriter_and_code(src: str) -> str:
    module = cst.parse_module(src)
    res = assertion_rewriter.assertion_rewriter_stage({"module": module})
    new_mod = res.get("module")
    assert new_mod is not None
    return new_mod.code


def test_assert_equal_rewrites_to_comparison():
    src = "self.assertEqual(1, 2)"
    code = _run_rewriter_and_code(src)
    assert "assert 1 == 2" in code


def test_assert_true_and_false_rewrite():
    src = '''self.assertTrue(x)
self.assertFalse(y)'''
    code = _run_rewriter_and_code(src)
    assert "assert x" in code
    assert "assert not y" in code


def test_assert_in_and_not_in():
    src = "self.assertIn(a, b)\nself.assertNotIn(c, d)"
    code = _run_rewriter_and_code(src)
    assert "assert a in b" in code
    assert "assert c not in d" in code


def test_assert_almost_equal_uses_pytest_approx():
    src = "self.assertAlmostEqual(a, b)"
    code = _run_rewriter_and_code(src)
    # should request pytest.approx usage
    assert "pytest.approx" in code


def test_assert_raises_context_manager_to_pytest_raises():
    src = "with self.assertRaises(ValueError):\n    f()"
    code = _run_rewriter_and_code(src)
    assert "with pytest.raises(ValueError):" in code
