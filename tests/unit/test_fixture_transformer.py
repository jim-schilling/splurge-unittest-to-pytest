from splurge_unittest_to_pytest.transformers.fixture_transformer import transform_fixtures_string_based


def test_transform_fixtures_string_based_with_body():
    code = """
class TestX(unittest.TestCase):
    def setUp(self):
        self.x = 1
    def tearDown(self):
        del self.x
"""
    out = transform_fixtures_string_based(code)
    assert "@pytest.fixture" in out
    assert "def setup_method(self):" in out
    assert "del self.x" not in out  # tearDown should be removed


def test_transform_fixtures_string_based_empty_body():
    code = """
class TestX(unittest.TestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass
"""
    out = transform_fixtures_string_based(code)
    assert "@pytest.fixture" in out
    assert "yield" in out
