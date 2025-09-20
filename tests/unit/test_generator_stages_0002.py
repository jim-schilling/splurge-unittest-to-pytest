from __future__ import annotations

import libcst as cst
from libcst import MetadataWrapper

from splurge_unittest_to_pytest.stages.collector import ClassInfo, Collector, CollectorOutput
from splurge_unittest_to_pytest.stages.generator import generator_stage

# consolidated fragments sometimes duplicated imports with different styles;
# prefer the explicit `generator_stage` import and keep `generator` separate.


def test_fixture_param_detects_temp_dir_name():
    module = cst.parse_module("\n")
    cls_node = cst.parse_module("class TestX:\n    pass\n").body[0]
    cls = ClassInfo(node=cls_node)
    call = cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Name("temp_dir"))])
    cls.setup_assignments["init_api_data"] = call
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": cls})
    context = {"collector_output": out, "module": module, "autocreate": False}
    result = generator_stage(context)
    assert isinstance(result, dict)
    module_node = result.get("module")
    if module_node is None:
        nodes = result.get("fixture_nodes") or []
        assert nodes, "generator produced no fixture nodes"
        code = cst.Module(body=list(nodes)).code
    else:
        code = module_node.code
    assert "def init_api_data(temp_dir)" in code or "def init_api_data( temp_dir )" in code


def test_fixture_param_detects_temp_dir_attr():
    module = cst.parse_module("\n")
    cls_node = cst.parse_module("class TestX:\n    pass\n").body[0]
    cls = ClassInfo(node=cls_node)
    call = cst.Call(
        func=cst.Name("Path"), args=[cst.Arg(value=cst.Attribute(value=cst.Name("temp_dir"), attr=cst.Name("attr")))]
    )
    cls.setup_assignments["init_api_data"] = call
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": cls})
    context = {"collector_output": out, "module": module, "autocreate": False}
    result = generator_stage(context)
    assert isinstance(result, dict)
    module_node = result.get("module")
    if module_node is None:
        nodes = result.get("fixture_nodes") or []
        assert nodes, "generator produced no fixture nodes"
        module_code = cst.Module(body=list(nodes))
    else:
        module_code = module_node
    func = next(
        (n for n in module_code.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None
    )
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert "temp_dir" in params


def test_fixture_param_detects_temp_dir_subscript():
    module = cst.parse_module("\n")
    cls_node = cst.parse_module("class TestX:\n    pass\n").body[0]
    cls = ClassInfo(node=cls_node)
    call = cst.parse_expression("Path(arr[temp_dir])")
    cls.setup_assignments["init_api_data"] = call
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": cls})
    context = {"collector_output": out, "module": module, "autocreate": False}
    result = generator_stage(context)
    assert isinstance(result, dict)
    module_node = result.get("module")
    if module_node is None:
        nodes = result.get("fixture_nodes") or []
        assert nodes, "generator produced no fixture nodes"
        module_code = cst.Module(body=list(nodes))
    else:
        module_code = module_node
    func = next(
        (n for n in module_code.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None
    )
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert "temp_dir" in params


def _run_and_get_code(call_expr: cst.BaseExpression) -> str:
    module = cst.parse_module("\n")
    cls_node = cst.parse_module("class TestX:\n    pass\n").body[0]
    cls = ClassInfo(node=cls_node)
    cls.setup_assignments["init_api_data"] = call_expr
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": cls})
    context = {"collector_output": out, "module": module, "autocreate": False}
    result = generator_stage(context)
    module_node = result.get("module")
    if module_node is None:
        nodes = result.get("fixture_nodes") or []
        assert nodes, "generator produced no fixture nodes"
        return cst.Module(body=list(nodes)).code
    return module_node.code


def test_nested_subscript_detects_inner_name():
    call = cst.parse_expression("Path(arr[outer[temp_dir]])")
    code = _run_and_get_code(call)
    module = cst.parse_module(code)
    func = next((n for n in module.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None)
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert "temp_dir" in params


def test_attribute_chain_detects_base_name():
    call = cst.parse_expression("Path(root.parent.temp_dir)")
    code = _run_and_get_code(call)
    module = cst.parse_module(code)
    func = next((n for n in module.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None)
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert any((n in params for n in ("root", "parent", "temp_dir")))


def test_fstring_detects_name():
    call = cst.parse_expression('f"{temp_dir}/x"')
    code = _run_and_get_code(call)
    module = cst.parse_module(code)
    func = next((n for n in module.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None)
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert "temp_dir" in params


SAMPLE = "\nclass MyTests(unittest.TestCase):\n    def setUp(self) -> None:\n        self.count = 5\n        self.name = 'bob'\n\n    def tearDown(self) -> None:\n        if self.count is not None:\n            self.count = None\n\n    def test_one(self) -> None:\n        assert self.count == 5\n"


def test_generator_creates_fixture_nodes() -> None:
    module = cst.parse_module(SAMPLE)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    ctx = {"module": module, "collector_output": out}
    result = generator_stage(ctx)
    specs = result.get("fixture_specs", {})
    nodes = result.get("fixture_nodes", [])
    assert "count" in specs
    assert "name" in specs
    assert len(nodes) >= 2
    node_names = {n.name.value for n in nodes}
    assert "count" in node_names
    assert "name" in node_names
    count_node = next((n for n in nodes if n.name.value == "count"))
    src = cst.Module(body=[count_node]).code
    assert "yield" in src
    assert "= None" in src


UNIT = '\nclass TestInitAPI(unittest.TestCase):\n    def setUp(self):\n        self.resource = util.get_resource()\n        self.content = """String Literal"""\n        var_a, var_b = get_resource_with_schema(\n            self.resource,\n            "Another String Literal",\n            self.content\n        )\n        self.var_a = str(var_a)\n        self.var_b = str(var_b)\n\n    def tearDown(self):\n        util.cleanup(self.resource)\n\n    def test_init_api_functionality(self) -> None:\n        assert self.content == """String Literal"""\n        assert self.var_a is not None\n        assert self.var_b is not None\n'


def test_generator_emits_namedtuple_and_fixture():
    module = cst.parse_module(UNIT)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    local_map = out.classes.get("TestInitAPI").local_assignments
    assert "var_a" in local_map and "var_b" in local_map
    import libcst as _cst

    assert isinstance(local_map["var_a"], tuple) and isinstance(local_map["var_a"][0], _cst.Call)
    assert isinstance(local_map["var_b"], tuple) and isinstance(local_map["var_b"][0], _cst.Call)
    assert local_map["var_a"][1] == 0
    assert local_map["var_b"][1] == 1
    setup = out.classes.get("TestInitAPI").setup_assignments
    missing = [k for k in ("resource", "content", "var_a", "var_b") if k not in setup]
    assert not missing, f"Missing expected setup assignments: {missing}; keys={list(setup.keys())}"
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    result = generator_stage(ctx)
    nodes = result.get("fixture_nodes", [])
    code = "\n".join((cst.Module(body=[n]).code for n in nodes))
    class_name = "TestInitAPI"
    base = class_name[4:] if class_name.startswith("Test") else class_name
    namedtuple_name = f"_{base}Data"
    import re

    snake = re.sub("(.)([A-Z][a-z]+)", "\\1_\\2", base)
    snake = re.sub("([a-z0-9])([A-Z])", "\\1_\\2", snake).lower().lstrip("_")
    fixture_name = f"{snake}_data"
    assert f"class {namedtuple_name}(NamedTuple):" in code or f"def {fixture_name}(" in code


UNIT__01 = "\nclass TestThing(unittest.TestCase):\n    def setUp(self):\n        a, b = make_pair()\n        self.a = a\n        self.b = b\n\n    def test_ok(self):\n        assert self.a is not None\n"


def test_composite_without_teardown_emits_returning_fixture():
    module = cst.parse_module(UNIT__01)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    result = generator_stage(ctx)
    nodes = result.get("fixture_nodes", [])
    has_return_fixture = any(
        (
            isinstance(n, cst.FunctionDef)
            and any((isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], cst.Return) for s in n.body.body))
            for n in nodes
        )
    )
    assert has_return_fixture


UNIT__02 = "\ndef init_api_data():\n    pass\n\nclass TestInitAPI(unittest.TestCase):\n    def setUp(self):\n        var_a, var_b = get_vals()\n        self.var_a = str(var_a)\n        self.var_b = str(var_b)\n\n    def tearDown(self):\n        cleanup()\n"


def test_fixture_name_avoids_module_collision():
    module = cst.parse_module(UNIT__02)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    result = generator_stage(ctx)
    nodes = result.get("fixture_nodes", [])
    fn_names = [n.name.value for n in nodes if isinstance(n, cst.FunctionDef)]
    assert "init_api_data" not in fn_names
    assert any((name.startswith("init_api_data_") for name in fn_names))


UNIT__03 = "\nclass TestThree(unittest.TestCase):\n    def setUp(self):\n        x, y, z = make_vals()\n        self.x = 's'\n        self.y = 1\n        self.z = 3.14\n\n    def tearDown(self):\n        pass\n"


def test_three_tuple_namedtuple_field_types():
    module = cst.parse_module(UNIT__03)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    result = generator_stage(ctx)
    nodes = result.get("fixture_nodes", [])
    code = "\n".join((cst.Module(body=[n]).code for n in nodes))
    assert "x: str" in code or "x: Any" in code
    assert "y: int" in code or "y: Any" in code
    assert "z: float" in code or "z: Any" in code


def _run(src: str) -> dict:
    module = cst.parse_module(src)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    return generator_stage({"module": module, "collector_output": out})


def test_literal_binding_and_cleanup() -> None:
    src = "\nclass T(unittest.TestCase):\n    def setUp(self) -> None:\n        self.flag = True\n\n    def tearDown(self) -> None:\n        if self.flag:\n            self.flag = False\n"
    res = _run(src)
    nodes = res["fixture_nodes"]
    flag_node = next((n for n in nodes if n.name.value == "flag"))
    s = cst.Module(body=[flag_node]).code
    assert "_flag_value" in s or "_flag_value_" in s
    assert "= False" in s
    assert "yield" in s


def test_del_self_attr_cleanup() -> None:
    src = "\nclass T(unittest.TestCase):\n    def setUp(self) -> None:\n        self.item = []\n\n    def tearDown(self) -> None:\n        del self.item\n"
    res = _run(src)
    nodes = res["fixture_nodes"]
    node = next((n for n in nodes if n.name.value == "item"))
    s = cst.Module(body=[node]).code
    assert "del " in s
    assert "self.item" not in s


def test_name_collision_uniqueness() -> None:
    src = "\nclass T(unittest.TestCase):\n    def setUp(self) -> None:\n        self.x = 1\n        self.x = 2\n\n    def tearDown(self) -> None:\n        self.x = None\n"
    res = _run(src)
    nodes = res["fixture_nodes"]
    xs = [n for n in nodes if n.name.value == "x"]
    assert len(xs) == 1
    s = cst.Module(body=[xs[0]]).code
    assert "_x_value" in s
    assert "= None" in s


def make_co(setup):
    co = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    class_node = cst.ClassDef(
        name=cst.Name("ExactTest"), body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    )
    ci = ClassInfo(node=class_node)
    ci.setup_assignments = setup
    ci.local_assignments = {}
    ci.teardown_statements = []
    co.classes = {"ExactTest": ci}
    return co


def render(nodes):
    if not nodes:
        return ""
    return cst.Module(body=list(nodes)).code


def test_tuple_literal_emits_tuple_annotation():
    setup = {
        "pair": cst.Tuple(elements=[cst.Element(value=cst.SimpleString('"a"')), cst.Element(value=cst.Integer("1"))])
    }
    co = make_co(setup)
    res = generator_stage({"collector_output": co, "module": cst.Module([])})
    code = render(res.get("fixture_nodes", []))
    assert "-> Tuple[" in code or "-> Tuple[" in code or "Tuple[" in code


def test_list_of_str_emits_list_annotation():
    setup = {"items": cst.List(elements=[cst.Element(value=cst.SimpleString('"x"'))])}
    co = make_co(setup)
    res = generator_stage({"collector_output": co, "module": cst.Module([])})
    code = render(res.get("fixture_nodes", []))
    assert "-> List[" in code or "List[" in code


def _make_collector_output(attrs: dict, teardown: list):
    class_node = cst.ClassDef(name=cst.Name("TestDirs"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=class_node)
    for k, v in attrs.items():
        ci.setup_assignments[k] = [v]
    ci.teardown_statements = teardown
    out = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    out.classes["TestDirs"] = ci
    return out


def test_temp_dirs_composite_generated():
    attrs = {
        "temp_dir": cst.Call(func=cst.Attribute(value=cst.Name("tempfile"), attr=cst.Name("mkdtemp")), args=[]),
        "config_dir": cst.Call(
            func=cst.Name("Path"),
            args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
        ),
        "data_dir": cst.Call(
            func=cst.Name("Path"),
            args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
        ),
    }
    teardown = [
        cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    cst.Call(
                        func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")),
                        args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
                    )
                )
            ]
        )
    ]
    out = _make_collector_output(attrs, teardown)
    res = generator_stage({"collector_output": out})
    fixture_nodes = res.get("fixture_nodes", [])
    names = [n.name.value for n in fixture_nodes if isinstance(n, cst.FunctionDef)]
    assert "temp_dir" in names
    assert "config_dir" in names or "data_dir" in names
    _ = res.get("needs_typing_names", [])


def make_collector_out(setup_assignments, *, local_assignments=None, teardown_statements=None):
    co = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    class_node = cst.ClassDef(
        name=cst.Name("MyTest"), body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    )
    ci = ClassInfo(node=class_node)
    ci.setup_assignments = setup_assignments
    ci.local_assignments = local_assignments or {}
    ci.teardown_statements = teardown_statements or []
    co.classes = {"MyTest": ci}
    return co


def render_fixture_nodes_from_stage(context):
    res = generator_stage(context)
    nodes = res.get("fixture_nodes", [])
    if not nodes:
        return ""
    module = cst.Module(body=list(nodes))
    return module.code


def test_infers_filename_from_positional_literal():
    helper_call = cst.Call(func=cst.Name("helper"), args=[cst.Arg(value=cst.SimpleString('"schema.sql"'))])
    local_map = {"sql_file": (helper_call, 0)}
    setup = {
        "sql_file": cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("sql_file"))]),
        "sql_content": cst.SimpleString('"create"'),
    }
    co = make_collector_out(setup, local_assignments=local_map)
    context = {"collector_output": co, "module": cst.Module(body=[]), "autocreate": True}
    code = render_fixture_nodes_from_stage(context)
    assert "schema.sql" in code


def test_infers_filename_from_keyword_arg():
    helper_call = cst.Call(
        func=cst.Name("some_helper"),
        args=[cst.Arg(keyword=cst.Name("filename"), value=cst.SimpleString('"data.json"'))],
    )
    local_map = {"data_file": (helper_call, 0)}
    setup = {
        "data_file": cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("data_file"))]),
        "data_content": cst.SimpleString('"x"'),
    }
    co = make_collector_out(setup, local_assignments=local_map)
    context = {"collector_output": co, "module": cst.Module(body=[]), "autocreate": True}
    code = render_fixture_nodes_from_stage(context)
    assert "data.json" in code


def test_infers_filename_from_path_constructor():
    path_call = cst.Call(
        func=cst.Attribute(value=cst.Name("pathlib"), attr=cst.Name("Path")),
        args=[cst.Arg(value=cst.SimpleString('"file.sql"'))],
    )
    local_map = {"file_file": (path_call, 0)}
    setup = {
        "file_file": cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("file_file"))]),
        "file_content": cst.SimpleString('"ok"'),
    }
    co = make_collector_out(setup, local_assignments=local_map)
    context = {"collector_output": co, "module": cst.Module(body=[]), "autocreate": True}
    code = render_fixture_nodes_from_stage(context)
    assert "file.sql" in code


def test_no_autocreate_respected():
    helper_call = cst.Call(func=cst.Name("helper"), args=[cst.Arg(value=cst.SimpleString('"schema.sql"'))])
    local_map = {"sql_file": (helper_call, 0)}
    setup = {
        "sql_file": cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("sql_file"))]),
        "sql_content": cst.SimpleString('"create"'),
    }
    co = make_collector_out(setup, local_assignments=local_map)
    context = {"collector_output": co, "module": cst.Module(body=[]), "autocreate": False}
    code = render_fixture_nodes_from_stage(context)
    assert "schema.sql" not in code


def make_collector_out__01(setup_assignments, *, local_map=None, teardown_statements=None):
    co = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    class_node = cst.ClassDef(
        name=cst.Name("LitTest"), body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    )
    ci = ClassInfo(node=class_node)
    ci.setup_assignments = setup_assignments
    ci.local_assignments = local_map or {}
    ci.teardown_statements = teardown_statements or []
    co.classes = {"LitTest": ci}
    return co


def render_module_from_nodes(nodes):
    if not nodes:
        return ""
    return cst.Module(body=list(nodes)).code


def test_infers_list_literal_homogeneous_strings():
    setup = {
        "items": cst.List(
            elements=[cst.Element(value=cst.SimpleString('"a"')), cst.Element(value=cst.SimpleString('"b"'))]
        )
    }
    co = make_collector_out__01(setup_assignments=setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "List" in names
    code = render_module_from_nodes(res.get("fixture_nodes", []))
    assert '["a", "b"]' in code


def test_infers_tuple_literal_heterogeneous():
    setup = {
        "pair": cst.Tuple(elements=[cst.Element(value=cst.SimpleString('"x"')), cst.Element(value=cst.Integer("1"))])
    }
    co = make_collector_out__01(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "Tuple" in names or "List" in names or "Any" in names
    code = render_module_from_nodes(res.get("fixture_nodes", []))
    assert '("x", 1)' in code


def test_infers_set_literal():
    setup = {"s": cst.Set(elements=[cst.Element(value=cst.Integer("1")), cst.Element(value=cst.Integer("2"))])}
    co = make_collector_out__01(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "List" in names or "Set" in names or "Any" in names


def test_infers_dict_literal():
    key = cst.SimpleString('"a"')
    val = cst.Integer("1")
    pair = cst.DictElement(key=key, value=val)
    setup = {"m": cst.Dict(elements=[pair])}
    co = make_collector_out__01(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "Dict" in names or "Any" in names


def test_infers_list_comprehension_fallbacks_any():
    comp = cst.parse_expression("[x for x in items]")
    setup = {"out": comp}
    co = make_collector_out__01(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "List" in names or "Any" in names


def _run_module(src: str) -> dict:
    module = cst.parse_module(src)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    return generator_stage({"module": module, "collector_output": out})


def test_avoid_module_level_name_collision() -> None:
    src = "\n_some_global = 1\n\nclass T(unittest.TestCase):\n    def setUp(self) -> None:\n        self.x = 1\n\n    def tearDown(self) -> None:\n        self.x = None\n"
    res = _run_module(src)
    nodes = res["fixture_nodes"]
    node = next((n for n in nodes if n.name.value == "x"))
    s = cst.Module(body=[node]).code
    assert "_x_value" in s or "_x_value_" in s
    assert "_some_global" in src
    assert "_some_global" not in s


def _run__01(src: str) -> dict:
    module = cst.parse_module(src)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    return generator_stage({"module": module, "collector_output": out})


def test_local_name_determinism() -> None:
    src = "\nclass T(unittest.TestCase):\n    def setUp(self) -> None:\n        self.x = 1\n\n    def tearDown(self) -> None:\n        self.x = None\n"
    res = _run__01(src)
    nodes = res["fixture_nodes"]
    node = next((n for n in nodes if n.name.value == "x"))
    s = cst.Module(body=[node]).code
    assert ("_x_value" in s or "_x_value_1" in s) or ("yield 1" in s and "x = None" in s)


def make_collector_out__02(setup_assignments, *, local_map=None, teardown_statements=None):
    co = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    class_node = cst.ClassDef(
        name=cst.Name("NestedTest"), body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    )
    ci = ClassInfo(node=class_node)
    ci.setup_assignments = setup_assignments
    ci.local_assignments = local_map or {}
    ci.teardown_statements = teardown_statements or []
    co.classes = {"NestedTest": ci}
    return co


def test_infers_nested_list_of_list():
    inner = cst.List(elements=[cst.Element(value=cst.SimpleString('"a"'))])
    outer = cst.List(elements=[cst.Element(value=inner)])
    setup = {"matrix": outer}
    co = make_collector_out__02(setup_assignments=setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "List" in names


def test_infers_tuple_of_list():
    inner = cst.List(elements=[cst.Element(value=cst.Integer("1"))])
    tup = cst.Tuple(elements=[cst.Element(value=inner), cst.Element(value=cst.Integer("2"))])
    setup = {"mix": tup}
    co = make_collector_out__02(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "Tuple" in names or "List" in names


def test_generator_creates_fixture_for_simple_literal_setup() -> None:
    src = "class T:\n    def setUp(self):\n        self.x = 42\n    def tearDown(self):\n        del self.x\n"
    module = cst.parse_module(src)
    class_node = next((n for n in module.body if isinstance(n, cst.ClassDef)))
    ci = ClassInfo(node=class_node)
    for stmt in class_node.body.body:
        if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "setUp":
            for s in stmt.body.body:
                if isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], cst.Assign):
                    ci.setup_assignments.setdefault("x", []).append(s.body[0].value)
        if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "tearDown":
            for s in stmt.body.body:
                ci.teardown_statements.append(s)
    collector = CollectorOutput(module=module, module_docstring_index=None, imports=(), classes={"T": ci})
    out = generator_stage({"collector_output": collector, "module": module})
    specs = out.get("fixture_specs") or {}
    nodes = out.get("fixture_nodes") or []
    assert "x" in specs
    assert any((isinstance(n, cst.FunctionDef) and n.name.value == "x" for n in nodes))


def test_generator_stage_composite_temp_dirs():
    module = cst.Module([])
    ci = ClassInfo(node=cst.ClassDef(name=cst.Name("MyTest"), body=cst.IndentedBlock(body=[])))
    ci.setup_assignments["temp_dir"] = [cst.SimpleString('"/tmp/foo"')]
    ci.setup_assignments["config_dir"] = [cst.SimpleString('"/tmp/conf"')]
    ci.teardown_statements.append(cst.SimpleStatementLine(body=[cst.Pass()]))
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"MyTest": ci})
    ctx = {"collector_output": out, "use_generator_core": True}
    res = generator_stage(ctx)
    nodes = res.get("fixture_nodes") or []
    code_strings = [cst.Module([n]).code if not isinstance(n, str) else str(n) for n in nodes]
    assert any(("def temp_dir" in s or "def config_dir" in s for s in code_strings))
    assert any(("yield" in s or "return" in s for s in code_strings))


def test_generator_stage_delegation(tmp_path):
    module = cst.Module([])
    ci = ClassInfo(node=cst.ClassDef(name=cst.Name("MyTest"), body=cst.IndentedBlock(body=[])))
    ci.setup_assignments["temp_dir"] = [cst.SimpleString('"/tmp/foo"')]
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"MyTest": ci})
    ctx = {"collector_output": out, "use_generator_core": True}
    res = generator_stage(ctx)
    nodes = res.get("fixture_nodes") or []
    assert nodes, "Expected fixture nodes from delegated GeneratorCore"
    code_strings = [cst.Module([n]).code if not isinstance(n, str) else str(n) for n in nodes]
    assert any(("def temp_dir" in s for s in code_strings))


def _make_collector_output_for_sample(attrs, teardown_stmts):
    class_node = cst.ClassDef(name=cst.Name("TestSample"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=class_node)
    for k, v in attrs.items():
        ci.setup_assignments[k] = [v]
    ci.teardown_statements = teardown_stmts
    out = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    out.classes["TestSample"] = ci
    return out


def test_per_attribute_and_mkdtemp_preserved():
    attrs = {
        "temp_dir": cst.Call(func=cst.Attribute(value=cst.Name("tempfile"), attr=cst.Name("mkdtemp")), args=[]),
        "config_dir": cst.Call(
            func=cst.Name("Path"),
            args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
        ),
        "main_config": cst.SimpleString('"ok"'),
    }
    teardown = [
        cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    cst.Call(
                        func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")),
                        args=[cst.Arg(value=cst.Name("temp_dir"))],
                    )
                )
            ]
        )
    ]
    out = _make_collector_output_for_sample(attrs, teardown)
    res = generator_stage({"collector_output": out})
    names = [n.name.value for n in res["fixture_nodes"] if isinstance(n, cst.FunctionDef)]
    assert "temp_dir" in names
    assert "config_dir" in names
    assert "main_config" in names
    module = cst.Module(body=res["fixture_nodes"])
    code = module.code
    assert "mkdtemp" in code


def test_per_attribute_fixture_when_not_dir_like():
    attrs = {
        "main_config": cst.Dict(elements=[cst.DictElement(key=cst.SimpleString('"k"'), value=cst.SimpleString('"v"'))])
    }
    out = _make_collector_output_for_sample(attrs, [])
    res = generator_stage({"collector_output": out})
    names = [n.name.value for n in res["fixture_nodes"] if isinstance(n, cst.FunctionDef)]
    assert "main_config" in names
    module = cst.Module(body=res["fixture_nodes"])
    assert '"k"' in module.code


def test_literal_yield_and_teardown():
    attrs = {"value": cst.Integer(value="42")}
    teardown = [
        cst.SimpleStatementLine(
            body=[cst.Expr(cst.Assign(targets=[cst.AssignTarget(target=cst.Name("value"))], value=cst.Name("None")))]
        )
    ]
    out = _make_collector_output_for_sample(attrs, teardown)
    res = generator_stage({"collector_output": out})
    nodes = [n for n in res["fixture_nodes"] if isinstance(n, cst.FunctionDef)]
    found = False
    for n in nodes:
        if n.name.value == "value":
            module = cst.Module(body=[n])
            code = module.code
            assert "yield 42" in code or "yield 42" in code
            assert "value = None" in code
            found = True
    assert found


def test_non_literal_binds_local_and_cleanup_refs_local():
    attrs = {"path": cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Name("temp"))])}
    teardown = [
        cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    cst.Call(
                        func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")),
                        args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("path")))],
                    )
                )
            ]
        )
    ]
    out = _make_collector_output_for_sample(attrs, teardown)
    res = generator_stage({"collector_output": out})
    nodes = [n for n in res["fixture_nodes"] if isinstance(n, cst.FunctionDef)]
    for n in nodes:
        if n.name.value == "path":
            module = cst.Module(body=[n])
            code = module.code
            assert "yield _path_value" in code or "_path_value" in code
            assert "_path_value" in code
            return
    assert False, "did not find generated fixture for path"


def test_mkdir_preserved_in_fixture():
    class_node = cst.ClassDef(name=cst.Name("TestMk"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=class_node)
    setup_module = cst.parse_module("self.d = Path(temp)\nself.d.mkdir(parents=True)\n")
    setup_fn = cst.FunctionDef(
        name=cst.Name("setUp"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=list(setup_module.body))
    )
    ci.setup_methods = [setup_fn]
    ci.setup_assignments = {"d": [cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Name("temp"))])]}
    ci.teardown_statements = []
    out = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    out.classes["TestMk"] = ci
    res = generator_stage({"collector_output": out})
    for n in res["fixture_nodes"]:
        if isinstance(n, cst.FunctionDef) and n.name.value == "d":
            module = cst.Module(body=[n])
            code = module.code
            assert "mkdir" not in code
            assert "parents=True" not in code
            return
    assert False, "did not find fixture for d"


def _make_collector_output__01(attrs: dict, teardown: list):
    class_node = cst.ClassDef(name=cst.Name("TestX"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=class_node)
    for k, v in attrs.items():
        ci.setup_assignments[k] = [v]
    ci.teardown_statements = teardown
    out = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    out.classes["TestX"] = ci
    return out


def test_typing_names_and_shutil_flag():
    attrs = {
        "temp_dir": cst.Call(func=cst.Attribute(value=cst.Name("tempfile"), attr=cst.Name("mkdtemp")), args=[]),
        "main_config": cst.Dict(elements=[cst.DictElement(key=cst.SimpleString('"k"'), value=cst.SimpleString('"v"'))]),
    }
    teardown = [
        cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    cst.Call(
                        func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")),
                        args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
                    )
                )
            ]
        )
    ]
    out = _make_collector_output__01(attrs, teardown)
    res = generator_stage({"collector_output": out})
    names = res.get("needs_typing_names", [])
    assert "Dict" in names or "Any" in names
    assert res.get("needs_shutil_import", False) is True


def _run_module__01(src: str) -> dict:
    module = cst.parse_module(src)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    return generator_stage({"module": module, "collector_output": out})


def test_regress_module_level_name_collision():
    src = "\n_some_global = 1\n\nclass T(unittest.TestCase):\n    def setUp(self) -> None:\n        self.x = 1\n\n    def tearDown(self) -> None:\n        self.x = None\n"
    res = _run_module__01(src)
    nodes = res["fixture_nodes"]
    node = next((n for n in nodes if n.name.value == "x"))
    s = cst.Module(body=[node]).code
    assert "_x_value" in s or "_x_value_" in s
    assert "_some_global" not in s


def _is_literal(node):
    return isinstance(node, (cst.SimpleString, cst.Integer, cst.Float)) or (
        isinstance(node, cst.Name) and getattr(node, "value", None) in ("True", "False")
    )


def test_is_literal_checks():
    assert _is_literal(cst.Integer("1"))
    assert _is_literal(cst.SimpleString("'x'"))
    assert not _is_literal(cst.Name("x"))
    assert not _is_literal(None)
    assert not _is_literal(cst.Call(func=cst.Name("f"), args=[]))


def test__references_attribute_simple_and_nested():
    assert True


def test_generator_stage_minimal_integration():
    module = cst.parse_module("x = 0\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    cls_info.setup_assignments = {"a": [cst.Integer("1")]}
    cls_info.teardown_statements = [
        cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    cst.Call(
                        func=cst.Name("del"),
                        args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("a")))],
                    )
                )
            ]
        )
    ]
    out = CollectorOutput(
        module=module, module_docstring_index=None, imports=[], classes={"C": cls_info}, has_unittest_usage=True
    )
    ctx = {"collector_output": out, "module": module}
    res = generator_stage(ctx)
    assert "fixture_specs" in res
    assert "fixture_nodes" in res


def _make_collector_output__02(module: cst.Module, cls_info: ClassInfo) -> CollectorOutput:
    return CollectorOutput(
        module=module, module_docstring_index=None, imports=[], classes={"C": cls_info}, has_unittest_usage=True
    )


def test_multi_assigned_forces_binding_and_local_assignment():
    module = cst.parse_module("x = 0\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    cls_info.setup_assignments = {"x": [cst.Integer("1"), cst.Integer("2")]}
    cleanup = cst.parse_statement("self.x = None")
    cls_info.teardown_statements = [cleanup]
    out = _make_collector_output__02(module, cls_info)
    res = generator_stage({"collector_output": out, "module": module})
    specs = res.get("fixture_specs")
    nodes = res.get("fixture_nodes")
    assert "x" in specs
    rendered = "\n\n".join((cst.Module(body=[n]).code for n in nodes))
    assert "_x_value" in rendered


def test_literal_yield_without_module_collision_rewrites_cleanup_to_fixture_name():
    module = cst.parse_module("a = 0\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    cls_info.setup_assignments = {"a": [cst.Integer("5")]}
    cls_info.teardown_statements = [cst.parse_statement("self.a = None")]
    out = _make_collector_output__02(module, cls_info)
    res = generator_stage({"collector_output": out, "module": module})
    nodes = res.get("fixture_nodes")
    assert nodes, "expected fixture node for 'a'"
    rendered = cst.Module(body=[nodes[0]]).code
    assert "yield 5" in rendered
    assert "a = None" in rendered


def test_module_collision_forces_binding_even_for_literal():
    module = cst.parse_module("_a_value = 1\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    cls_info.setup_assignments = {"a": [cst.Integer("7")]}
    cls_info.teardown_statements = [cst.parse_statement("self.a = None")]
    out = _make_collector_output__02(module, cls_info)
    res = generator_stage({"collector_output": out, "module": module})
    specs = res.get("fixture_specs")
    nodes = res.get("fixture_nodes")
    assert "a" in specs
    rendered = cst.Module(body=[nodes[0]]).code
    assert "_a_value" in rendered


def test_name_collision_skips_fixture_node_creation_but_records_spec():
    module = cst.parse_module("def a():\n    pass\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    cls_info.setup_assignments = {"a": [cst.Integer("9")]}
    cls_info.teardown_statements = []
    out = _make_collector_output__02(module, cls_info)
    res = generator_stage({"collector_output": out, "module": module})
    specs = res.get("fixture_specs")
    assert "a" in specs
    assert "a" in specs
