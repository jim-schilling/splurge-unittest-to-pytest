from splurge_unittest_to_pytest.main import convert_string

DOMAINS = ["main"]


def test_transformer_emits_guard_fixture_for_self_referential_setup():
    src = """
class T(unittest.TestCase):
    def setUp(self):
        self.sql_file = sql_file

    def test_it(self):
        assert True
"""
    # Use the public conversion API (staged pipeline) to perform the conversion
    res = convert_string(src)
    code = res.converted_code
    # Check that a fixture named sql_file exists and the test uses it as a parameter
    assert "def sql_file(" in code
    assert "def test_it(sql_file)" in code or "def test_it(sql_file):" in code
