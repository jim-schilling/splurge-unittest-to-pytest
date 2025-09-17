import libcst as cst

from splurge_unittest_to_pytest.converter import fixtures


def test_choose_unique_name_collision():
    existing = {"_foo_value", "_foo_value_1", "other"}
    # _choose_unique_name is internal but exercised via public API that uses it
    name = fixtures._choose_unique_name("_foo_value", existing)
    assert name == "_foo_value_2"


def test_infer_simple_return_annotation_literals():
    ann = fixtures._infer_simple_return_annotation(cst.Integer("1"))
    assert isinstance(ann, cst.Annotation)
    assert isinstance(ann.annotation, cst.Name)
    assert ann.annotation.value == "int"

    ann = fixtures._infer_simple_return_annotation(cst.SimpleString("'x'"))
    assert ann.annotation.value == "str"


def test_create_simple_fixture_fallback_binds_local(tmp_path):
    # complex expression: a call -> should bind to a local and return that name
    call = cst.Call(func=cst.Name("make_value"))
    fn = fixtures.create_simple_fixture("my_fixture", call)
    # body should contain an Assign followed by Return
    stmts = list(fn.body.body)
    assert any(isinstance(s.body[0], cst.Assign) for s in stmts)
    assert any(isinstance(s.body[0], cst.Return) for s in stmts)
    # returns annotation should be None for fallback
    assert fn.returns is None


def test_create_simple_fixture_with_guard_self_reference():
    # expression that is a direct Name equal to attr_name should trigger guard
    expr = cst.Name("amb")
    fn = fixtures.create_simple_fixture_with_guard("amb", expr)
    # guard emits a Raise in the body
    assert any(isinstance(s.body[0], cst.Raise) for s in fn.body.body)


def test_create_autocreated_file_fixture_variants():
    # without content fixture name -> uses empty string literal write
    fn = fixtures.create_autocreated_file_fixture("sql_file")
    # params should include tmp_path only
    assert len(fn.params.params) == 1
    assert fn.returns is not None and isinstance(fn.returns.annotation, cst.Name)

    # with content fixture name -> params include it
    fn2 = fixtures.create_autocreated_file_fixture("sql_file", content_fixture_name="sql_content")
    names = [p.name.value for p in fn2.params.params]
    assert "tmp_path" in names and "sql_content" in names

    # explicit filename should appear in the joinpath call as string literal
    fn3 = fixtures.create_autocreated_file_fixture("sql_file", filename="custom.sql")
    # inspect the first Assign -> Call arg string
    assign = fn3.body.body[0]
    assert isinstance(assign.body[0], cst.Assign)
    # the call argument should be the repr of filename
    call = assign.body[0].value
    assert isinstance(call, cst.Call)


def test_create_fixture_for_attribute_delegates_to_cleanup_and_guard():
    # when cleanup exists, create_fixture_for_attribute should produce a yield-based fixture
    cleanup_stmt = cst.parse_statement("cleanup()")
    teardown = {"file": [cleanup_stmt]}
    fn = fixtures.create_fixture_for_attribute("file", cst.SimpleString("'x'"), teardown)
    # should be a FunctionDef with a Yield in body (yield-based fixture)
    assert any(isinstance(s.body[0], cst.Expr) and isinstance(s.body[0].value, cst.Yield) for s in fn.body.body)

    # when no cleanup and self-referential, guard should be used
    fn2 = fixtures.create_fixture_for_attribute("amb", cst.Name("amb"), {})
    assert any(isinstance(s.body[0], cst.Raise) for s in fn2.body.body)


def test_create_simple_fixture_simple_literal_annotation_and_return():
    fn = fixtures.create_simple_fixture("num", cst.Integer("1"))
    # should return the literal directly
    first = fn.body.body[0]
    assert isinstance(first.body[0], cst.Return)
    assert isinstance(first.body[0].value, cst.Integer)
    # returns annotation should indicate int
    assert isinstance(fn.returns, cst.Annotation)
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "int"


def test_create_fixture_with_cleanup_replaces_attr_name_in_cleanup():
    attr = "data"
    cleanup_stmt = cst.parse_statement("do_cleanup(data)")
    fn = fixtures.create_fixture_with_cleanup(attr, cst.SimpleString("'x'"), [cleanup_stmt])
    # find the cleanup call expression in the body (should be after yield)
    calls = [s for s in fn.body.body if isinstance(s.body[0], cst.Expr) and isinstance(s.body[0].value, cst.Call)]
    assert calls, "expected a cleanup call in fixture body"
    call = calls[-1].body[0].value
    # arg should be a Name with the local value name (starts with _data_value)
    arg0 = call.args[0].value
    assert isinstance(arg0, cst.Name)
    assert arg0.value.startswith("_data_value")


def test_create_autocreated_file_fixture_write_args_inspected():
    fn = fixtures.create_autocreated_file_fixture("sql_file")
    # second statement should be the write_call
    write_stmt = fn.body.body[1]
    assert isinstance(write_stmt.body[0], cst.Expr)
    write_call = write_stmt.body[0].value
    # arg should be the empty string literal when no content fixture provided
    assert isinstance(write_call.args[0].value, cst.SimpleString)
    assert write_call.args[0].value.value == "''"

    fn2 = fixtures.create_autocreated_file_fixture("sql_file", content_fixture_name="sql_content")
    write_stmt2 = fn2.body.body[1]
    write_call2 = write_stmt2.body[0].value
    assert isinstance(write_call2.args[0].value, cst.Name)
    assert write_call2.args[0].value.value == "sql_content"


def test_collect_identifiers_from_statements_and_choose_unique_name_no_collision():
    stmts = [cst.parse_statement("a = 1"), cst.parse_statement("b = 2")]
    ids = fixtures._collect_identifiers_from_statements(stmts)
    assert "a" in ids and "b" in ids
    # choose unique when base not in existing
    name = fixtures._choose_unique_name("_new_value", ids)
    assert name == "_new_value"


def test_infer_simple_return_annotation_containers():
    ann = fixtures._infer_simple_return_annotation(cst.List([]))
    assert isinstance(ann.annotation, cst.Name) and ann.annotation.value == "List"
    ann = fixtures._infer_simple_return_annotation(cst.Tuple([]))
    assert ann.annotation.value == "Tuple"
    ann = fixtures._infer_simple_return_annotation(cst.Set([cst.Element(value=cst.Integer("1"))]))
    assert ann.annotation.value == "Set"
    ann = fixtures._infer_simple_return_annotation(
        cst.Dict([cst.DictElement(key=cst.SimpleString("'k'"), value=cst.Integer("1"))])
    )
    assert ann.annotation.value == "Dict"


def test_attribute_chain_does_not_trigger_guard():
    # self.x.y should not be considered self-referential for attr 'y'
    expr = cst.Attribute(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")), attr=cst.Name("y"))
    fn = fixtures.create_simple_fixture_with_guard("y", expr)
    assert not any(isinstance(s.body[0], cst.Raise) for s in fn.body.body)


def test_infer_none_and_collect_identifiers_handles_bad_stmt():
    # infer None should return None
    assert fixtures._infer_simple_return_annotation(None) is None

    # _collect_identifiers_from_statements should ignore non-statement objects
    bad = object()
    ids = fixtures._collect_identifiers_from_statements([bad, cst.parse_statement("z = 1")])
    assert "z" in ids


def test_is_self_referential_subscript_index_hits_true():
    # create subscript like amb[amb] which should detect inner Name
    sub = cst.Subscript(value=cst.Name("amb"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("amb")))])
    assert fixtures._is_self_referential(sub, "amb")


def test_create_simple_fixture_none_fallback():
    fn = fixtures.create_simple_fixture("noney", None)
    # fallback path binds to a local and returns it
    assert any(isinstance(s.body[0], cst.Assign) for s in fn.body.body)
    assert any(isinstance(s.body[0], cst.Return) for s in fn.body.body)
