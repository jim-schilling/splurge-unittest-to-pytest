import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_transformer as at


def test_transform_assert_equal_basic():
    call = cst.Call(func=cst.Name("assertEqual"), args=[cst.Arg(value=cst.Name("a")), cst.Arg(value=cst.Name("b"))])
    out = at.transform_assert_equal(call)
    assert isinstance(out, cst.Assert)
    # the Assert.test should be a Comparison with Equal
    assert isinstance(out.test, cst.Comparison)


def test_transform_assert_true_false():
    t = cst.Call(func=cst.Name("assertTrue"), args=[cst.Arg(value=cst.Name("cond"))])
    f = cst.Call(func=cst.Name("assertFalse"), args=[cst.Arg(value=cst.Name("cond"))])
    ot = at.transform_assert_true(t)
    of = at.transform_assert_false(f)
    assert isinstance(ot, cst.Assert)
    assert isinstance(of, cst.Assert)
    # false should be a UnaryOperation with Not
    assert isinstance(of.test, cst.UnaryOperation)


def test_transform_assert_regex_and_not_regex():
    call = cst.Call(
        func=cst.Name("assertRegex"), args=[cst.Arg(value=cst.Name("s")), cst.Arg(value=cst.SimpleString('"p"'))]
    )
    out = at.transform_assert_regex(call, re_alias=None, re_search_name=None)
    assert isinstance(out, cst.Assert)

    call2 = cst.Call(
        func=cst.Name("assertNotRegex"), args=[cst.Arg(value=cst.Name("s")), cst.Arg(value=cst.SimpleString('"p"'))]
    )
    out2 = at.transform_assert_not_regex(call2)
    assert isinstance(out2, cst.Assert)
