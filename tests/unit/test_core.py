from splurge_unittest_to_pytest.converter import core


def test_core_exports():
    # Ensure the core module re-exports expected symbols
    assert hasattr(core, "SelfReferenceRemover")
    assert hasattr(core, "normalize_method_name")
