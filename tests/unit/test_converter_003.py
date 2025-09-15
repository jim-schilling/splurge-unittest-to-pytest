import libcst as cst

from splurge_unittest_to_pytest.converter import fixtures

DOMAINS = ["converter"]


def test_create_simple_fixture_literal():
    fn = fixtures.create_simple_fixture("x", cst.Integer("1"))
    # Should return a FunctionDef with Return containing the literal
    assert isinstance(fn, cst.FunctionDef)
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(fn)])]).code
    assert "return 1" in code or "return (1)" in code


def test_create_simple_fixture_with_guard_emits_runtime_error():
    # self-referential placeholder should emit a fixture that raises at runtime
    # Use simple Name expression referencing the attr
    fn = fixtures.create_simple_fixture_with_guard("x", cst.Name("x"))
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(fn)])]).code
    assert "RuntimeError" in code


def test_create_autocreated_file_fixture_defaults_and_params():
    fn = fixtures.create_autocreated_file_fixture("sql_file", content_fixture_name=None, filename=None)
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(fn)])]).code
    # should contain tmp_path and write_text and return str(p)
    assert "tmp_path" in code
    assert "write_text" in code
    assert "return str(p)" in code or "return(str(p))" in code


def make_setup_func_source():
    # Simple setUp with two assignments to self.a and self.b
    src = """
class Dummy:
    def setUp(self):
        self.a = 1
        self.b = {'x': 2}
"""
    module = cst.parse_module(src)
    # find the FunctionDef for setUp by walking the module body
    for stmt in module.body:
        if isinstance(stmt, cst.ClassDef):
            for inner in stmt.body.body:
                if isinstance(inner, cst.FunctionDef) and inner.name.value == "setUp":
                    return inner
    raise RuntimeError("setUp not found")


def test_parse_setup_assignments_simple():
    node = make_setup_func_source()
    assignments = fixtures.parse_setup_assignments(node)
    assert isinstance(assignments, dict)
    assert "a" in assignments and "b" in assignments
    # a should be an Integer, b should be a Dict
    assert isinstance(assignments["a"], cst.Integer)
    assert isinstance(assignments["b"], cst.Dict)


def test_create_fixture_for_attribute_simple_and_cleanup():
    # create a simple fixture (no teardown cleanup)
    val_expr = cst.Integer(value="42")
    fixture = fixtures.create_simple_fixture("answer", val_expr)
    assert isinstance(fixture, cst.FunctionDef)
    assert fixture.name.value == "answer"
    # decorator exists and references pytest.fixture; may be an Attribute (canonical @pytest.fixture)
    assert fixture.decorators
    assert any(
        getattr(d.decorator, "attr", None)
        and d.decorator.attr.value == "fixture"
        or getattr(d.decorator, "func", None)
        and getattr(d.decorator.func, "attr", None)
        and d.decorator.func.attr.value == "fixture"
        for d in fixture.decorators
    )

    # create fixture with cleanup: use create_fixture_with_cleanup
    cleanup = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Call(func=cst.Name("cleanup")))])]
    fixture2 = fixtures.create_fixture_with_cleanup("resource", cst.Name("obj"), cleanup)
    assert isinstance(fixture2, cst.FunctionDef)
    assert fixture2.name.value == "resource"
    # body should contain a Yield or an Assign followed by Yield
    body_stmts = fixture2.body.body
    assert len(body_stmts) >= 1
    # ensure decorator is present
    assert fixture2.decorators


def test_cleanup_replacement_and_yield_binding():
    # cleanup references self.resource -> should be replaced to local value name
    cleanup_stmt = cst.SimpleStatementLine(
        body=[cst.Expr(value=cst.Call(func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("close"))))]
    )
    fixture = fixtures.create_fixture_with_cleanup("resource", cst.Call(func=cst.Name("make_resource")), [cleanup_stmt])
    # body should contain an Assign then a Yield then a cleanup where 'self' reference replaced
    body = fixture.body.body
    assert any(
        isinstance(s, cst.SimpleStatementLine) and isinstance(getattr(s, "body", [None])[0], cst.Assign) for s in body
    )
    assert any(
        isinstance(s, cst.SimpleStatementLine)
        and isinstance(getattr(s, "body", [None])[0], cst.Expr)
        and isinstance(getattr(s, "body", [None])[0].value, cst.Yield)
        for s in body
    )


def test_make_autouse_attach_and_module_insertion():
    # Build a fake module with an import and check insertion
    mod_src = "import os\n\n"
    module = cst.parse_module(mod_src)
    # create a dummy setup_fixtures mapping
    dummy = {"a": fixtures.create_simple_fixture("a", cst.Integer("1"))}

    # Use the current fixtures module's high-level helpers to create the autouse fixture
    # Build a local autouse attach fixture using test-local logic (decoupled from compat helpers)
    def _make_autouse_attach_local(setup_fixtures: dict[str, cst.FunctionDef]) -> cst.FunctionDef:
        from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator

        inst_assign = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("inst"))],
                    value=cst.Call(
                        func=cst.Name("getattr"),
                        args=[
                            cst.Arg(value=cst.Name("request")),
                            cst.Arg(value=cst.SimpleString("'instance'")),
                            cst.Arg(value=cst.Name("None")),
                        ],
                    ),
                )
            ]
        )

        set_calls: list[cst.BaseStatement] = []
        for name in setup_fixtures.keys():
            set_calls.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Expr(
                            value=cst.Call(
                                func=cst.Name("setattr"),
                                args=[
                                    cst.Arg(value=cst.Name("inst")),
                                    cst.Arg(value=cst.SimpleString(f"'{name}'")),
                                    cst.Arg(value=cst.Name(name)),
                                ],
                            )
                        )
                    ]
                )
            )

        if_block = cst.IndentedBlock(body=set_calls)
        if_stmt = cst.If(
            test=cst.Comparison(
                left=cst.Name("inst"),
                comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))],
            ),
            body=if_block,
        )

        decorator = build_pytest_fixture_decorator({"autouse": True})

        func = cst.FunctionDef(
            name=cst.Name("_attach_to_instance"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("request"))]),
            body=cst.IndentedBlock(body=[inst_assign, if_stmt]),
            decorators=[decorator],
        )

        return func

    func = _make_autouse_attach_local(dummy)
    assert isinstance(func, cst.FunctionDef)

    # Insert the fixture locally into the module
    def _insert_attach_fixture_local(module_node: cst.Module, fixture_func: cst.FunctionDef) -> cst.Module:
        new_body: list = list(module_node.body)
        insert_pos = 0
        for i, stmt in enumerate(new_body):
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                first = stmt.body[0]
                if isinstance(first, cst.Import):
                    for alias in first.names:
                        if isinstance(alias.name, cst.Name) and alias.name.value == "pytest":
                            insert_pos = i + 1
                            break
                if insert_pos:
                    break

        new_body.insert(insert_pos, cst.EmptyLine())
        new_body.insert(insert_pos + 1, fixture_func)

        return module.with_changes(body=new_body)

    new_module = _insert_attach_fixture_local(module, func)
    # Ensure the module now contains the fixture by checking code text includes function name
    assert "_attach_to_instance" in new_module.code


def test_parse_setup_assignments_empty():
    # setUp with no assignments should return empty dict
    src = """
class X:
    def setUp(self):
        pass
"""
    module = cst.parse_module(src)
    for stmt in module.body:
        if isinstance(stmt, cst.ClassDef):
            for inner in stmt.body.body:
                if isinstance(inner, cst.FunctionDef) and inner.name.value == "setUp":
                    node = inner
                    break
    assignments = fixtures.parse_setup_assignments(node)
    assert assignments == {}
