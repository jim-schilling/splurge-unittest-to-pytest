from splurge_unittest_to_pytest import main

DOMAINS = ["core"]


def test_pattern_configurator_add_and_match():
    p = main.PatternConfigurator()
    # initial patterns contain common names
    assert p._is_setup_method("setUp")
    assert p._is_teardown_method("tearDown")
    assert p._is_test_method("test_something")

    # add new patterns and verify matching
    p.add_setup_pattern("setupAll")
    assert p._is_setup_method("setupAllFeature")

    p.add_test_pattern("describe_")
    assert p._is_test_method("describe_feature")
