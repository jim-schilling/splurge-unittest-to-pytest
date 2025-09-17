import libcst as cst
from splurge_unittest_to_pytest.converter.call_utils import is_self_call
from splurge_unittest_to_pytest.converter.assertion_dispatch import convert_assertion


def test_is_self_call_positive_and_negative():
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("foo")), args=[cst.Arg(value=cst.Integer("1"))]
    )
    res = is_self_call(call)
    assert res is not None
    name, args = res
    assert name == "foo"
    assert len(args) == 1
    call2 = cst.Call(func=cst.Attribute(value=cst.Name("other"), attr=cst.Name("bar")), args=[])
    assert is_self_call(call2) is None


def test_convert_assertion_returns_none_for_raises_and_unknown():
    from libcst import Arg

    assert convert_assertion("assertRaises", []) is None
    assert convert_assertion("no_such_assertion", [Arg(value=cst.Integer("1"))]) is None
