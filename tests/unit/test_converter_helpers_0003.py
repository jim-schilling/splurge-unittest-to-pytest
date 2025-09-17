from splurge_unittest_to_pytest.converter import helpers

DOMAINS = ["core"]


def test_core_exports():
    # Ensure the helpers module exposes expected symbols formerly available via core shim
    assert hasattr(helpers, "SelfReferenceRemover")
    assert hasattr(helpers, "normalize_method_name")
