from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_transform_fixtures_string_based_with_body():
    code = """
class TestX(unittest.TestCase):
    def setUp(self):
        self.x = 1
    def tearDown(self):
        del self.x
"""
    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)
    assert "@pytest.fixture" in out
    assert "def setup_method" in out
    # tearDown content should be incorporated into teardown portion (yield-based)
    assert "del self.x" in out or "yield" in out


def test_transform_fixtures_string_based_empty_body():
    code = """
class TestX(unittest.TestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass
"""
    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)
    assert "@pytest.fixture" in out
    assert "yield" in out
