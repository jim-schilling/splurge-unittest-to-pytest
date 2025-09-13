import warnings

import libcst as cst

from splurge_unittest_to_pytest.converter import UnittestToPytestTransformer


def test_transformer_pattern_properties_and_adders():
    # Creating the transformer should emit a DeprecationWarning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        transformer = UnittestToPytestTransformer()
        # one DeprecationWarning expected
        assert any(isinstance(x.message, DeprecationWarning) for x in w)

    # default patterns are non-empty sets
    assert transformer.setup_patterns
    assert transformer.teardown_patterns
    assert transformer.test_patterns

    # adding patterns updates the underlying sets (case-insensitive for setup/teardown)
    transformer.add_setup_pattern("custom_setup")
    assert "custom_setup" in {p.lower() for p in transformer.setup_patterns}

    transformer.add_teardown_pattern("custom_teardown")
    assert "custom_teardown" in {p.lower() for p in transformer.teardown_patterns}

    transformer.add_test_pattern("describe_")
    assert any(p == "describe_" for p in transformer.test_patterns)


def test_remove_self_references_delegation():
    transformer = UnittestToPytestTransformer()
    # Create a small module containing a self attribute access in a function body
    src = "class A:\n    def test_one(self):\n        self.x = 1\n"
    module = cst.parse_module(src)
    # Ensure the helper doesn't raise and returns a CSTNode when applied
    node = transformer._remove_self_references(module)
    assert isinstance(node, cst.CSTNode)
