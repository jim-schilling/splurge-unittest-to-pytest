import libcst as cst

from splurge_unittest_to_pytest.transformers.parametrize_helper import _make_parametrize_call


def test_make_parametrize_call_basic():
    rows = [(cst.Integer(value="1"),), (cst.Integer(value="2"),)]
    deco = _make_parametrize_call(param_names=("x",), rows=rows, include_ids=False)

    assert isinstance(deco, cst.Decorator)
    call = deco.decorator
    assert isinstance(call, cst.Call)
    func = call.func
    # Should be pytest.mark.parametrize
    assert isinstance(func, cst.Attribute)
    assert isinstance(func.attr, cst.Name) and func.attr.value == "parametrize"


def test_make_parametrize_call_with_ids():
    rows = [(cst.Integer(value="10"), cst.SimpleString(value='"a"'))]
    deco = _make_parametrize_call(param_names=("i", "s"), rows=rows, include_ids=True)

    call = deco.decorator
    # Expect three args: param names, data list, and ids kwarg
    assert isinstance(call, cst.Call)
    assert len(call.args) == 3
    # Last arg should be keyword 'ids'
    ids_arg = call.args[2]
    assert ids_arg.keyword is not None and isinstance(ids_arg.keyword, cst.Name)
    assert ids_arg.keyword.value == "ids"
