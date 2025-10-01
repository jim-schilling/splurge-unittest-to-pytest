def test_import_generators_and_tasks():
    # Ensure package __init__ modules import cleanly (quick coverage bump)
    import importlib

    importlib.import_module("splurge_unittest_to_pytest.generators")
    importlib.import_module("splurge_unittest_to_pytest.tasks")
