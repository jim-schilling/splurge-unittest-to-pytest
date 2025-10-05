"""Tests for question `condition` and `process` lambdas in InteractiveConfigBuilder workflows."""

from types import SimpleNamespace

from splurge_unittest_to_pytest.config_validation import InteractiveConfigBuilder


def _get_question_by_key(questions, key):
    for q in questions:
        if q.get("key") == key:
            return q
    return None


def test_legacy_workflow_conditions_and_process():
    builder = InteractiveConfigBuilder()
    cfg, interaction = builder._legacy_migration_workflow()
    questions = interaction["questions"]

    # backup_root condition depends on backup_originals
    q_backup_root = _get_question_by_key(questions, "backup_root")
    assert q_backup_root is not None
    cond = q_backup_root.get("condition")
    # When config.backup_originals is True -> condition True
    cobj = SimpleNamespace(backup_originals=True)
    assert cond(cobj) is True
    cobj2 = SimpleNamespace(backup_originals=False)
    assert cond(cobj2) is False

    # file_patterns process splits comma-separated strings
    q_file_patterns = _get_question_by_key(questions, "file_patterns")
    proc = q_file_patterns.get("process")
    assert proc("test_*.py, spec_*.py") == ["test_*.py", "spec_*.py"]

    # test_method_prefixes condition depends on use_prefixes
    q_prefixes = _get_question_by_key(questions, "test_method_prefixes")
    cond2 = q_prefixes.get("condition")
    assert cond2(SimpleNamespace(use_prefixes=True)) is True
    assert cond2(SimpleNamespace(use_prefixes=False)) is False
    assert q_prefixes.get("process")("a,b") == ["a", "b"]


def test_modern_workflow_processes():
    builder = InteractiveConfigBuilder()
    cfg, interaction = builder._modern_framework_workflow()
    questions = interaction["questions"]

    q_prefixes = _get_question_by_key(questions, "test_method_prefixes")
    proc = q_prefixes.get("process")
    assert proc("test,spec,should,it") == ["test", "spec", "should", "it"]


def test_custom_workflow_processes():
    builder = InteractiveConfigBuilder()
    cfg, interaction = builder._custom_setup_workflow()
    questions = interaction["questions"]

    q_file_patterns = _get_question_by_key(questions, "file_patterns")
    proc = q_file_patterns.get("process")
    assert proc("test_*.py,spec_*.py") == ["test_*.py", "spec_*.py"]

    q_prefixes = _get_question_by_key(questions, "test_method_prefixes")
    proc2 = q_prefixes.get("process")
    assert proc2("test") == ["test"]
