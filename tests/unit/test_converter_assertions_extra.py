import libcst as cst

from splurge_unittest_to_pytest.converter import assertions


def call_assert_helper(helper, src_args):
    # Build libcst.Arg objects from source strings
    args = [cst.Arg(value=cst.parse_expression(s)) for s in src_args]
    node = helper(args)
    # Render the assert as a small statement inside a module for textual checks
    stmt = cst.SimpleStatementLine(body=[node])
    return node, cst.Module(body=[stmt]).code


def test_assert_equal_and_not_equal():
    eq_node, eq_code = call_assert_helper(assertions._assert_equal, ["a", "b"])
    assert isinstance(eq_node, cst.Assert)
    assert "a == b" in eq_code

    neq_node, neq_code = call_assert_helper(assertions._assert_not_equal, ["a", "b"])
    assert "a != b" in neq_code


def test_assert_true_and_false():
    t_node, t_code = call_assert_helper(assertions._assert_true, ["x > 0"])
    assert "x > 0" in t_code

    f_node, f_code = call_assert_helper(assertions._assert_false, ["ok"])
    # assert not ok
    assert "not ok" in f_code


def test_assert_is_none_and_is_not_none_behaviour():
    # Non-literal becomes an 'is None' comparison
    is_none_node, is_none_code = call_assert_helper(assertions._assert_is_none, ["var"])
    assert "is None" in is_none_code

    # Literal returns None to avoid bad code like `assert 1 is None`
    assert assertions._assert_is_none([cst.Arg(value=cst.Integer("1"))]) is None

    is_not_none_node, is_not_none_code = call_assert_helper(assertions._assert_is_not_none, ["x"])
    assert "is not None" in is_not_none_code


def test_in_not_in_and_isinstance():
    inn_node, inn_code = call_assert_helper(assertions._assert_in, ["item", "coll"])
    assert "in coll" in inn_code

    notin_node, notin_code = call_assert_helper(assertions._assert_not_in, ["i", "c"])
    assert "not in c" in notin_code

    inst_node, inst_code = call_assert_helper(assertions._assert_is_instance, ["val", "T"])
    # should call isinstance
    assert "isinstance(val, T)" in inst_code

    notinst_node, notinst_code = call_assert_helper(assertions._assert_not_is_instance, ["val", "T"])
    assert "not isinstance" in notinst_code


def test_comparison_helpers():
    gt_node, gt_code = call_assert_helper(assertions._assert_greater, ["a", "b"])
    assert "> b" in gt_code

    ge_node, ge_code = call_assert_helper(assertions._assert_greater_equal, ["a", "b"])
    assert ">= b" in ge_code

    lt_node, lt_code = call_assert_helper(assertions._assert_less, ["a", "b"])
    assert "< b" in lt_code

    le_node, le_code = call_assert_helper(assertions._assert_less_equal, ["a", "b"])
    assert "<= b" in le_code


def test_assertions_map_contains_expected_and_callable():
    # Spot-check that map contains some keys and callables
    for key in ("assertEqual", "assertTrue", "assertIsNone", "assertIn"):
        assert key in assertions.ASSERTIONS_MAP
        assert callable(assertions.ASSERTIONS_MAP[key])
