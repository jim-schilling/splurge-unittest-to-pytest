import libcst as cst

from splurge_unittest_to_pytest.transformers.fixture_transformer import create_teardown_fixture


def test_create_teardown_fixture_includes_yield_and_teardown_code():
    teardown = ["self.value = 42"]
    func = create_teardown_fixture(teardown)

    module = cst.Module(body=[func])
    code = module.code

    assert "def teardown_method" in code
    # yield should be present to model teardown
    assert "yield" in code
    # the provided teardown line should appear
    assert "self.value = 42" in code
    # decorator should be a pytest.fixture
    assert "@pytest.fixture" in code or "pytest.fixture" in code
