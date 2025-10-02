import libcst as cst

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


def test_transform_fixtures_string_based_empty_setup():
    """Test transform_fixtures_string_based with empty setUp method."""
    from splurge_unittest_to_pytest.transformers.fixture_transformer import transform_fixtures_string_based

    code = """
class TestX(unittest.TestCase):
    def setUp(self):
        pass
"""
    out = transform_fixtures_string_based(code)
    # Should generate fixture with pass statements (covers line 55)
    assert "@pytest.fixture" in out
    assert "def setup_method(self):" in out
    assert "pass" in out
    assert "yield" in out


def test_create_class_fixture_with_malformed_code():
    """Test create_class_fixture handles malformed setup/teardown code."""
    from splurge_unittest_to_pytest.transformers.fixture_transformer import create_class_fixture

    # Test with malformed code that will trigger exception handling (lines 111-112, 123-124)
    setup_code = ["invalid syntax here >>>"]
    teardown_code = ["also invalid <<<"]

    result = create_class_fixture(setup_code, teardown_code)
    # Should handle exceptions and create a valid fixture
    assert isinstance(result, cst.FunctionDef)
    assert result.name.value == "setup_class"


def test_create_class_fixture_empty_inputs():
    """Test create_class_fixture with empty input lists."""
    from splurge_unittest_to_pytest.transformers.fixture_transformer import create_class_fixture

    result = create_class_fixture([], [])
    # Should create fixture with default pass/yield structure (covers line 127)
    assert isinstance(result, cst.FunctionDef)
    assert result.name.value == "setup_class"


def test_create_instance_fixture_with_malformed_code():
    """Test create_instance_fixture handles malformed setup/teardown code."""
    from splurge_unittest_to_pytest.transformers.fixture_transformer import create_instance_fixture

    setup_code = ["invalid >>>"]
    teardown_code = ["also invalid <<<"]

    result = create_instance_fixture(setup_code, teardown_code)
    # Should handle exceptions gracefully
    assert isinstance(result, cst.FunctionDef)
    assert result.name.value == "setup_method"


def test_create_teardown_fixture_with_malformed_code():
    """Test create_teardown_fixture handles malformed teardown code."""
    from splurge_unittest_to_pytest.transformers.fixture_transformer import create_teardown_fixture

    teardown_code = ["invalid syntax <<<"]

    result = create_teardown_fixture(teardown_code)
    # Should handle exceptions gracefully
    assert isinstance(result, cst.FunctionDef)
    assert result.name.value == "teardown_method"


def test_create_module_fixture_with_malformed_code():
    """Test create_module_fixture handles malformed setup/teardown code."""
    from splurge_unittest_to_pytest.transformers.fixture_transformer import create_module_fixture

    setup_code = ["invalid >>>"]
    teardown_code = ["also invalid <<<"]

    result = create_module_fixture(setup_code, teardown_code)
    # Should handle exceptions gracefully
    assert isinstance(result, cst.FunctionDef)
    assert result.name.value == "setup_module"
