import libcst as cst

from splurge_unittest_to_pytest.converter.call_utils import is_self_call


def test_is_self_call_positive():
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("do_something")),
        args=[cst.Arg(value=cst.Integer("1"))],
    )
    res = is_self_call(call)
    assert res is not None
    name, args = res
    assert name == "do_something"
    assert len(args) == 1


def test_is_self_call_negative():
    call = cst.Call(func=cst.Name("do_something_else"), args=[])
    assert is_self_call(call) is None
