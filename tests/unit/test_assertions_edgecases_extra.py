import libcst as cst

from splurge_unittest_to_pytest.converter import assertions


def _a(expr: str) -> cst.Arg:
    return cst.Arg(value=cst.parse_expression(expr))


def test_assertion_fallbacks_on_missing_args():
    # Functions should return an Assert(Name('False')) when insufficient args
    fb = assertions._assert_equal([])
    assert isinstance(fb, cst.Assert)
    assert isinstance(fb.test, cst.Name) and fb.test.value == "False"

    fb2 = assertions._assert_true([])
    assert isinstance(fb2, cst.Assert)
    assert isinstance(fb2.test, cst.Name) and fb2.test.value == "False"

    fb3 = assertions._assert_in([_a("x")])
    assert isinstance(fb3, cst.Assert)
    assert isinstance(fb3.test, cst.Name) and fb3.test.value == "False"

    fb4 = assertions._assert_is_none([])
    assert isinstance(fb4, cst.Assert)
    assert isinstance(fb4.test, cst.Name) and fb4.test.value == "False"


def test_assertions_map_callability_and_non_crash():
    # Ensure ASSERTIONS_MAP is well-formed and calling entries doesn't raise
    arg1 = _a("1")
    arg2 = _a("2")
    for name, fn in assertions.ASSERTIONS_MAP.items():
        # Call with two args; functions may accept 1 or 2 args and should
        # either return an Assert or None, but should not raise.
        try:
            res = fn([arg1, arg2])
        except Exception as exc:  # pragma: no cover - defensive
            raise AssertionError(f"ASSERTIONS_MAP handler for {name} raised: {exc}")
        assert (res is None) or isinstance(res, cst.Assert)
