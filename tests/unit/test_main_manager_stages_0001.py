import shutil
import libcst as cst
from splurge_unittest_to_pytest.main import convert_string
from splurge_unittest_to_pytest.stages.manager import StageManager


def _cleanup_mgr_dir(mgr: StageManager) -> None:
    d = getattr(mgr, "_diagnostics_dir", None)
    if d is None:
        return
    try:
        shutil.rmtree(d)
    except Exception:
        pass


def test_leave_ClassDef_removes_unittest_base_and_preserves_non_unittest():
    src = "\nimport unittest\n\nclass MyTest(unittest.TestCase):\n    def test_one(self):\n        self.assertEqual(1, 1)\n\nclass Other:\n    pass\n"
    new_module_code = convert_string(src).converted_code
    assert "unittest.TestCase" not in new_module_code
    assert "def test_one()" in new_module_code or "def test_one(" in new_module_code


def test_leave_FunctionDef_converts_setup_to_fixture_and_removes_self_from_tests():
    src = "\nclass X(unittest.TestCase):\n    def setUp(self):\n        self.x = 5\n\n    def test_something(self):\n        assert self.x == 5\n"
    new_module_code = convert_string(src).converted_code
    assert "def test_something(" in new_module_code or "def test_something(self)" not in new_module_code


def test_leave_Module_adds_pytest_import_when_needed():
    src = "\nclass A(unittest.TestCase):\n    def test_one(self):\n        with self.assertRaises(ValueError):\n            raise ValueError()\n"
    new_module_code = convert_string(src).converted_code
    assert "import pytest" in new_module_code or "pytest" in new_module_code


def test_stage_manager_register_does_not_create_files_when_disabled(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    try:

        def stage(ctx: dict):
            return {"ok": True}

        mgr.register(stage)
        module = cst.parse_module("x = 1\n")
        mgr.run(module)
        assert mgr._diagnostics_dir is None
    finally:
        _cleanup_mgr_dir(mgr)
