import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import build_caplog_call


def test_build_caplog_call_defaults_to_info():
    call = cst.parse_expression("self.assertLogs('x')")
    assert isinstance(call, cst.Call)
    cap_call = build_caplog_call(call)
    assert isinstance(cap_call, cst.Call)
    assert isinstance(cap_call.func, cst.Attribute)
    assert cap_call.func.attr.value == "at_level"
    assert len(cap_call.args) == 1
    assert isinstance(cap_call.args[0].value, cst.SimpleString)
    assert cap_call.args[0].value.value == '"INFO"'
