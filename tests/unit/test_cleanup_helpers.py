import libcst as cst

from splurge_unittest_to_pytest.converter.cleanup import references_attribute, extract_relevant_cleanup


def test_references_attribute_simple_name():
    node = cst.Name("foo")
    assert references_attribute(node, "foo")
    assert not references_attribute(node, "bar")


def test_references_attribute_attribute_chain():
    node = cst.Attribute(value=cst.Name("self"), attr=cst.Name("x"))
    assert references_attribute(node, "x")
    assert references_attribute(node, "self")


def test_extract_relevant_cleanup_assign_and_call():
    # a = foo
    assign = cst.SimpleStatementLine(body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name("a"))], value=cst.Name("foo"))])
    # self.x.cleanup()
    call = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Call(func=cst.Attribute(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")), attr=cst.Name("cleanup")), args=[]))])

    stmts = [assign, call]
    res = extract_relevant_cleanup(stmts, "x")
    assert len(res) == 1
    assert res[0] is call


def test_references_attribute_in_call_args_and_subscript():
    # foo(bar(self.x)) and arr[self.x]
    inner_call = cst.Call(func=cst.Name("bar"), args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")))])
    call_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=inner_call)])

    sub = cst.Subscript(value=cst.Name("arr"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x"))))])
    sub_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=sub)])

    res = extract_relevant_cleanup([call_stmt, sub_stmt], "x")
    assert len(res) == 2


def test_extract_relevant_cleanup_if_and_indentedblock():
    # if self.x: inner_call()
    if_stmt = cst.If(test=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")), body=cst.IndentedBlock(body=[
        cst.SimpleStatementLine(body=[cst.Expr(value=cst.Call(func=cst.Name("inner_call"), args=[]))])
    ]))

    # orelse as IndentedBlock
    if_with_orelse = cst.If(test=cst.Name("flag"), body=cst.IndentedBlock(body=[
        cst.SimpleStatementLine(body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name("a"))], value=cst.Name("b"))])
    ]), orelse=cst.Else(body=cst.IndentedBlock(body=[
        cst.SimpleStatementLine(body=[cst.Expr(value=cst.Call(func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("cleanup")), args=[]))])
    ])))

    res = extract_relevant_cleanup([if_stmt, if_with_orelse], "x")
    # should find the inner_call only via attribute test, and cleanup in orelse
    assert any(isinstance(s, cst.If) for s in res)

