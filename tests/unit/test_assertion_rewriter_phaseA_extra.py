import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def _mod(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_assert_false_converts_to_not_expression():
    src = """
def test_it():
    self.assertFalse(x)
"""
    mod = _mod(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    # Expect assert not x
    assert "assert not x" in new_mod.code


def test_assert_true_on_nested_attr_keeps_attr():
    src = """
def test_it():
    self.assertTrue(foo.bar)
"""
    mod = _mod(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    assert "assert foo.bar" in new_mod.code


def test_assert_raises_context_manager_to_pytest_raises():
    src = """
def test_it():
    with self.assertRaises(ValueError):
        do_thing()
"""
    mod = _mod(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    assert "with pytest.raises(ValueError)" in new_mod.code
    # Ensure the stage indicates pytest import needed
    assert out.get("needs_pytest_import") is True


def test_assert_almost_equal_uses_approx_and_sets_pytest_flag():
    src = """
def test_it():
    self.assertAlmostEqual(a, b)
"""
    mod = _mod(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    # pytest.approx should appear
    assert "pytest.approx" in new_mod.code
    assert out.get("needs_pytest_import") is True


def test_assert_equal_with_msg_keyword_is_stripped():
    src = """
def test_it():
    self.assertEqual(1, 2, msg='boom')
"""
    mod = _mod(src)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    # message should not be present in final assert
    assert "boom" not in new_mod.code
