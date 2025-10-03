import libcst as cst

from splurge_unittest_to_pytest.transformers.parametrize_helper import (
    ParametrizeOptions,
    convert_subtest_loop_to_parametrize,
)


def _make_simple_subtest_func():
    # def test_one(self):
    #     for i in [1,2]:
    #         with self.subTest(i=i):
    #             pass
    inner_with = cst.With(items=[cst.WithItem(cst.Call(func=cst.Attribute(value=cst.Name(value='self'), attr=cst.Name(value='subTest')), args=[cst.Arg(keyword=cst.Name('i'), value=cst.Name('i'))]))], body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]))
    for_node = cst.For(target=cst.Name('i'), iter=cst.List([cst.Element(cst.Integer('1')), cst.Element(cst.Integer('2'))]), body=cst.IndentedBlock(body=[inner_with]))
    func = cst.FunctionDef(name=cst.Name('test_one'), params=cst.Parameters(params=[cst.Param(name=cst.Name('self'))]), body=cst.IndentedBlock(body=[for_node]))
    return func


def test_convert_with_options_respects_include_ids_false():
    func = _make_simple_subtest_func()
    options = ParametrizeOptions(parametrize_include_ids=False)
    converted = convert_subtest_loop_to_parametrize(func, func, options)
    assert converted is not None
    # Ensure decorator exists and that it's a Call with args (ids absent)
    decorators = list(converted.decorators or [])
    assert decorators
    call = decorators[0].decorator
    # When include_ids=False we expect only two positional args (names, data)
    assert isinstance(call, cst.Call)
    assert len(call.args) == 2
