import libcst as cst
from splurge_unittest_to_pytest.stages.generator import generator as generator_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo

DOMAINS = ["generator", "stages"]


def make_collector_out(setup_assignments, local_assignments=None, teardown_statements=None):
    # Build a CollectorOutput with minimal required fields so generator_stage can consume it.
    co = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    # Create a minimal ClassDef node for ClassInfo
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
    # local helper: helper('schema.sql') assigned to name 'sql_file'
    helper_call = cst.Call(func=cst.Name("helper"), args=[cst.Arg(value=cst.SimpleString('"schema.sql"'))])
    local_map = {"sql_file": (helper_call, 0)}
    setup = {
        "sql_file": cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("sql_file"))]),
        "sql_content": cst.SimpleString('"create"'),
    }
    co = make_collector_out(setup, local_map)
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
    co = make_collector_out(setup, local_map)
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
    co = make_collector_out(setup, local_map)
    context = {"collector_output": co, "module": cst.Module(body=[]), "autocreate": True}
    code = render_fixture_nodes_from_stage(context)
    assert "file.sql" in code


def test_no_autocreate_respected():
    # same shape as positional test but autocreate disabled
    helper_call = cst.Call(func=cst.Name("helper"), args=[cst.Arg(value=cst.SimpleString('"schema.sql"'))])
    local_map = {"sql_file": (helper_call, 0)}
    setup = {
        "sql_file": cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("sql_file"))]),
        "sql_content": cst.SimpleString('"create"'),
    }
    co = make_collector_out(setup, local_map)
    context = {"collector_output": co, "module": cst.Module(body=[]), "autocreate": False}
    code = render_fixture_nodes_from_stage(context)
    # When autocreate is disabled we shouldn't see the inferred filename in generated fixtures
    assert "schema.sql" not in code
