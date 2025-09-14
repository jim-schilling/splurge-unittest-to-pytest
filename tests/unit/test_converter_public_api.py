from splurge_unittest_to_pytest.main import PatternConfigurator, convert_string


def test_transformer_pattern_properties_and_adders():
    pc = PatternConfigurator()

    # default patterns are non-empty sets
    assert pc.setup_patterns
    assert pc.teardown_patterns
    assert pc.test_patterns

    # adding patterns updates the underlying sets
    pc.add_setup_pattern("custom_setup")
    assert "custom_setup" in {p.lower() for p in pc.setup_patterns}

    pc.add_teardown_pattern("custom_teardown")
    assert "custom_teardown" in {p.lower() for p in pc.teardown_patterns}

    pc.add_test_pattern("describe_")
    assert any(p == "describe_" for p in pc.test_patterns)


def test_remove_self_references_delegation():
    # Confirm conversion removes 'self.' references when appropriate
    src = "class A:\n    def test_one(self):\n        self.x = 1\n"
    res = convert_string(src)
    assert "self.x" not in res.converted_code
