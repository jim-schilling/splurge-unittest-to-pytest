import libcst as cst

from splurge_unittest_to_pytest.stages.pipeline import run_pipeline


def test_strict_mode_drops_classes_and_autouse():
    src = "\nimport unittest\n\nclass TestX(unittest.TestCase):\n    def setUp(self):\n        self.x = 1\n\n    def tearDown(self):\n        self.x = None\n\n    def test_a(self):\n        assert self.x == 1\n"
    mod = cst.parse_module(src)
    out = run_pipeline(mod, autocreate=False)
    code = out.code
    assert "class TestX" not in code
    assert "def _attach_to_instance(" not in code
    assert "def test_a(" in code


SAMPLE = '\n"""module doc"""\nimport os\n\nclass MyTests(unittest.TestCase):\n    def setUp(self) -> None:\n        self.r = open(\'f\')\n\n    def tearDown(self) -> None:\n        if self.r is not None:\n            self.r.close()\n\n    def test_one(self) -> None:\n        assert True\n'


def test_pipeline_runs_all_stages_and_inserts_fixtures_and_import() -> None:
    module = cst.parse_module(SAMPLE)
    new_mod = run_pipeline(module)
    imports = [s.body[0] for s in new_mod.body if isinstance(s, cst.SimpleStatementLine) and s.body]
    pytest_imports = [i for i in imports if isinstance(i, cst.Import) and i.names[0].name.value == "pytest"]
    assert len(pytest_imports) == 1
    fixtures = [n for n in new_mod.body if isinstance(n, cst.FunctionDef) and n.name.value == "r"]
    assert len(fixtures) == 1
    assert any((isinstance(n, cst.FunctionDef) and n.name.value == "test_one" for n in new_mod.body))
