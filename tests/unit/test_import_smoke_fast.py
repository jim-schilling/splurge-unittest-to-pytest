def test_import_cli_context_events_migration_orchestrator():
    # Importing should not raise and should be safe as a smoke test of public API
    import importlib

    modules = [
        "splurge_unittest_to_pytest.cli",
        "splurge_unittest_to_pytest.context",
        "splurge_unittest_to_pytest.events",
        "splurge_unittest_to_pytest.migration_orchestrator",
    ]

    for mod in modules:
        module = importlib.import_module(mod)
        assert module is not None
