import libcst as cst
from splurge_unittest_to_pytest.converter import UnittestToPytestTransformer


def test_transformer_emits_guard_fixture_for_self_referential_setup():
    src = """
class T(unittest.TestCase):
    def setUp(self):
        self.sql_file = sql_file

    def test_it(self):
        assert True
"""
    mod = cst.parse_module(src)
    transformer = UnittestToPytestTransformer(compat=False)
    new = mod.visit(transformer)
    code = new.code
    # Check that a fixture named sql_file exists and contains a RuntimeError or 'ambiguous'
    assert "def sql_file(" in code
    assert "RuntimeError" in code or "ambiguous" in code
