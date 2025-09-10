import libcst as cst
from splurge_unittest_to_pytest.stages.pipeline import run_pipeline

SAMPLE = '''
"""module doc"""
import os

class MyTests(unittest.TestCase):
    def setUp(self):
        self.r = open('f')

    def tearDown(self):
        if self.r is not None:
            self.r.close()

    def test_one(self):
        assert True
'''


def test_pipeline_runs_all_stages_and_inserts_fixtures_and_import():
    module = cst.parse_module(SAMPLE)
    new_mod = run_pipeline(module, compat=True)
    # check pytest import exists
    imports = [s.body[0] for s in new_mod.body if isinstance(s, cst.SimpleStatementLine) and s.body]
    pytest_imports = [i for i in imports if isinstance(i, cst.Import) and i.names[0].name.value == "pytest"]
    assert len(pytest_imports) == 1
    # check fixture exists
    fixtures = [n for n in new_mod.body if isinstance(n, cst.FunctionDef) and n.name.value == "r"]
    assert len(fixtures) == 1
    # check autouse attach exists
    attach = [n for n in new_mod.body if isinstance(n, cst.FunctionDef) and n.name.value == "_attach_to_instance"]
    assert len(attach) == 1
