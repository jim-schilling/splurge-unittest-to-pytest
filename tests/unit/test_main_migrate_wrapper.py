import tempfile
import textwrap
from pathlib import Path

from splurge_unittest_to_pytest import main as main_module
from splurge_unittest_to_pytest.result import Result, ResultStatus


def test_main_migrate_file_success(monkeypatch, tmp_path: Path):
    # Create a temporary python test file
    f = tmp_path / "test_sample.py"
    f.write_text("print('ok')")

    # Monkeypatch MigrationOrchestrator to return success for migrate_file
    class DummyResult:
        def __init__(self):
            self._success = True

        def is_success(self):
            return True

    class DummyOrch:
        def migrate_file(self, source_file, config=None):
            return DummyResult()

    monkeypatch.setattr("splurge_unittest_to_pytest.main.MigrationOrchestrator", lambda: DummyOrch())

    res = main_module.migrate([str(f)])
    assert res.is_success()
    assert str(f) in res.data


def test_main_migrate_file_failure(monkeypatch, tmp_path: Path):
    f = tmp_path / "test_sample.py"
    f.write_text("print('ok')")

    class DummyResult:
        def __init__(self):
            self._success = False
            self.error = Exception("fail")

        def is_success(self):
            return False

    class DummyOrch:
        def migrate_file(self, source_file, config=None):
            return DummyResult()

    monkeypatch.setattr("splurge_unittest_to_pytest.main.MigrationOrchestrator", lambda: DummyOrch())

    res = main_module.migrate([str(f)])
    assert res.is_error()
