import libcst as cst
from splurge_unittest_to_pytest.stages import generator as gen
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def test_generator_empty_context():
    assert gen.generator({}) == {}


def test_is_literal_checks():
    assert gen._is_literal(cst.SimpleString('"x"'))
    assert gen._is_literal(cst.Integer("1"))
    assert not gen._is_literal(cst.Name("x"))


def test_generator_creates_fixture_for_dir_like(tmp_path):
    module = cst.parse_module(
        "class TestX:\n    def setUp(self):\n        self.tmp_dir = Path('p')\n    def tearDown(self):\n        pass\n"
    )
    ci = ClassInfo(node=cst.ClassDef(name=cst.Name("TestX"), body=cst.IndentedBlock(body=[])))
    ci.setup_assignments = {"tmp_dir": [cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.SimpleString("'p'"))])]}
    ci.teardown_statements = []
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": ci})
    res = gen.generator({"collector_output": out})
    assert isinstance(res, dict)
    assert "fixture_specs" in res and "fixture_nodes" in res
    assert "tmp_dir" in res["fixture_specs"]


def test_generator_stage_alias_empty():
    assert gen.generator_stage({}) == {}
